"""
Playbook Storage Manager with Semantic Search

Provides comprehensive playbook storage with ChromaDB semantic search,
label management, and Redis caching for high performance.

Author: Lance James, Unit 221B, Inc
"""

import json
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("ChromaDB not available - semantic search disabled")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available - using fallback embeddings")

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - caching disabled")

from database import ControlDatabase
from playbook_engine import PlaybookEngine

logger = logging.getLogger(__name__)


class PlaybookStorageManager:
    """
    Manages playbook storage with semantic search and label management.

    Features:
    - ChromaDB semantic search with all-MiniLM-L6-v2 embeddings
    - Label-based filtering with AND/OR logic
    - Redis caching with automatic invalidation
    - Multiple identifier types (ID, slug, name, memory_id)
    """

    def __init__(
        self,
        db_path: str,
        chroma_path: str = "./data/chroma",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize playbook storage manager.

        Args:
            db_path: Path to SQLite database
            chroma_path: Path to ChromaDB storage
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            redis_password: Redis password (optional)
            embedding_model: Sentence transformer model name
        """
        self.db = ControlDatabase(db_path)
        self.playbook_engine = PlaybookEngine()

        # Initialize ChromaDB for semantic search
        self.chroma_client = None
        self.playbook_collection = None
        if CHROMADB_AVAILABLE:
            try:
                self.chroma_client = chromadb.PersistentClient(
                    path=chroma_path,
                    settings=Settings(anonymized_telemetry=False)
                )
                self.playbook_collection = self.chroma_client.get_or_create_collection(
                    name="playbook_embeddings",
                    metadata={"description": "Playbook semantic search embeddings"}
                )
                logger.info(f"ChromaDB initialized at {chroma_path}")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {e}")
                self.chroma_client = None

        # Initialize embedding model
        self.embedding_model = None
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
                logger.info(f"Loaded embedding model: {embedding_model}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")

        # Initialize Redis for caching
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = aioredis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=True
                )
                logger.info(f"Redis client initialized: {redis_host}:{redis_port}")
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")
                self.redis_client = None

        self.cache_ttl = 300  # 5 minutes

    async def store_playbook(
        self,
        name: str,
        content: Dict[str, Any],
        category: str = "general",
        labels: Optional[List[str]] = None,
        format_type: str = "yaml",
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Store a playbook with labels and automatic semantic indexing.

        Args:
            name: Playbook name
            content: Playbook content as dictionary
            category: Playbook category
            labels: List of labels (format: "name" or "name:value")
            format_type: Content format (yaml, json, toml)
            metadata: Additional metadata
            created_by: User ID who created the playbook

        Returns:
            Dictionary with playbook_id, slug, and status
        """
        try:
            # Validate playbook content
            content_str = json.dumps(content)
            slug = self._generate_slug(name)

            # Generate search tokens from name, category, and content
            search_tokens = self._generate_search_tokens(name, category, content)

            # Store in database
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO playbooks (name, slug, category, format, content,
                                          search_tokens, created_by, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name, slug, category, format_type, content_str,
                    search_tokens, created_by, datetime.now(), datetime.now()
                ))
                playbook_id = cursor.lastrowid
                conn.commit()

            # Add labels if provided
            if labels:
                await self._add_labels_to_playbook(playbook_id, labels, created_by)

            # Generate and store embedding for semantic search
            if self.chroma_client and self.embedding_model:
                await self._index_playbook_in_chroma(playbook_id, name, content, category, labels or [])

            logger.info(f"Stored playbook {playbook_id}: {name}")

            return {
                "playbook_id": playbook_id,
                "slug": slug,
                "name": name,
                "category": category,
                "labels": labels or [],
                "status": "stored"
            }

        except Exception as e:
            logger.error(f"Error storing playbook: {e}")
            raise

    async def search_playbooks(
        self,
        query: str = "",
        labels: Optional[List[str]] = None,
        category: Optional[str] = None,
        semantic_search: bool = True,
        similarity_threshold: float = 0.7,
        match_all_labels: bool = True,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search playbooks with semantic search and label filtering.

        Args:
            query: Search query for semantic search
            labels: List of labels to filter by
            category: Category to filter by
            semantic_search: Use semantic search if True, else full-text
            similarity_threshold: Minimum similarity score (0.0-1.0)
            match_all_labels: If True, match ALL labels (AND), else ANY (OR)
            limit: Maximum number of results

        Returns:
            List of matching playbooks with metadata
        """
        try:
            results = []

            # Semantic search via ChromaDB
            if semantic_search and query and self.chroma_client and self.embedding_model:
                results = await self._semantic_search(
                    query, labels, category, similarity_threshold, match_all_labels, limit
                )

            # Full-text search via SQLite
            else:
                results = await self._fulltext_search(
                    query, labels, category, match_all_labels, limit
                )

            return results

        except Exception as e:
            logger.error(f"Error searching playbooks: {e}")
            raise

    async def get_playbook(
        self,
        playbook_id: Optional[int] = None,
        slug: Optional[str] = None,
        name: Optional[str] = None,
        memory_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve playbook by ID, slug, name, or memory_id with Redis caching.

        Priority: id → slug → name → memory_id

        Args:
            playbook_id: Playbook database ID
            slug: Playbook slug
            name: Playbook name
            memory_id: Memory system ID

        Returns:
            Playbook dictionary or None if not found
        """
        try:
            # Check Redis cache first
            cache_key = f"playbook:{playbook_id or slug or name or memory_id}"
            if self.redis_client:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for {cache_key}")
                    return json.loads(cached)

            # Query database
            with self.db.get_connection() as conn:
                if playbook_id:
                    query = "SELECT * FROM playbooks WHERE id = ?"
                    params = (playbook_id,)
                elif slug:
                    query = "SELECT * FROM playbooks WHERE slug = ?"
                    params = (slug,)
                elif name:
                    query = "SELECT * FROM playbooks WHERE name = ?"
                    params = (name,)
                elif memory_id:
                    query = "SELECT * FROM playbooks WHERE embedding_metadata LIKE ?"
                    params = (f'%{memory_id}%',)
                else:
                    return None

                cursor = conn.execute(query, params)
                row = cursor.fetchone()

                if not row:
                    return None

                # Build playbook dictionary
                playbook = self._row_to_playbook_dict(row)

                # Get labels
                playbook['labels'] = await self._get_playbook_labels(playbook['id'])

                # Cache result
                if self.redis_client:
                    await self.redis_client.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(playbook)
                    )

                return playbook

        except Exception as e:
            logger.error(f"Error retrieving playbook: {e}")
            raise

    async def add_playbook_labels(
        self,
        playbook_id: int,
        labels: List[str],
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Add labels to existing playbook with ChromaDB metadata sync.

        Args:
            playbook_id: Playbook database ID
            labels: List of labels to add
            created_by: User ID adding the labels

        Returns:
            Dictionary with updated labels
        """
        try:
            await self._add_labels_to_playbook(playbook_id, labels, created_by)

            # Update ChromaDB metadata
            if self.chroma_client:
                await self._update_chroma_labels(playbook_id, labels, operation="add")

            # Invalidate cache
            await self._invalidate_cache(playbook_id)

            # Get updated labels
            updated_labels = await self._get_playbook_labels(playbook_id)

            logger.info(f"Added {len(labels)} labels to playbook {playbook_id}")

            return {
                "playbook_id": playbook_id,
                "labels_added": labels,
                "total_labels": len(updated_labels),
                "all_labels": updated_labels
            }

        except Exception as e:
            logger.error(f"Error adding playbook labels: {e}")
            raise

    async def remove_playbook_labels(
        self,
        playbook_id: int,
        labels: List[str]
    ) -> Dict[str, Any]:
        """
        Remove labels from playbook with cache invalidation.

        Args:
            playbook_id: Playbook database ID
            labels: List of labels to remove

        Returns:
            Dictionary with remaining labels
        """
        try:
            with self.db.get_connection() as conn:
                for label in labels:
                    label_name, label_value = self._parse_label(label)
                    if label_value:
                        conn.execute("""
                            DELETE FROM playbook_labels
                            WHERE playbook_id = ? AND label_name = ? AND label_value = ?
                        """, (playbook_id, label_name, label_value))
                    else:
                        conn.execute("""
                            DELETE FROM playbook_labels
                            WHERE playbook_id = ? AND label_name = ?
                        """, (playbook_id, label_name))
                conn.commit()

            # Update ChromaDB metadata
            if self.chroma_client:
                await self._update_chroma_labels(playbook_id, labels, operation="remove")

            # Invalidate cache
            await self._invalidate_cache(playbook_id)

            # Get remaining labels
            remaining_labels = await self._get_playbook_labels(playbook_id)

            logger.info(f"Removed {len(labels)} labels from playbook {playbook_id}")

            return {
                "playbook_id": playbook_id,
                "labels_removed": labels,
                "remaining_labels": len(remaining_labels),
                "all_labels": remaining_labels
            }

        except Exception as e:
            logger.error(f"Error removing playbook labels: {e}")
            raise

    async def list_playbook_labels(
        self,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all labels with usage statistics and filtering by category.

        Args:
            category: Filter labels by category (optional)
            limit: Maximum number of labels to return

        Returns:
            List of labels with usage counts
        """
        try:
            with self.db.get_connection() as conn:
                if category:
                    query = """
                        SELECT label_name, label_value, label_type, category,
                               COUNT(*) as usage_count,
                               MAX(created_at) as last_used
                        FROM playbook_labels
                        WHERE category = ?
                        GROUP BY label_name, label_value
                        ORDER BY usage_count DESC, label_name ASC
                        LIMIT ?
                    """
                    params = (category, limit)
                else:
                    query = """
                        SELECT label_name, label_value, label_type, category,
                               COUNT(*) as usage_count,
                               MAX(created_at) as last_used
                        FROM playbook_labels
                        GROUP BY label_name, label_value
                        ORDER BY usage_count DESC, label_name ASC
                        LIMIT ?
                    """
                    params = (limit,)

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                labels = []
                for row in rows:
                    label_str = row[0]
                    if row[1]:  # Has value
                        label_str = f"{row[0]}:{row[1]}"

                    labels.append({
                        "label": label_str,
                        "label_name": row[0],
                        "label_value": row[1],
                        "label_type": row[2],
                        "category": row[3],
                        "usage_count": row[4],
                        "last_used": row[5]
                    })

                return labels

        except Exception as e:
            logger.error(f"Error listing playbook labels: {e}")
            raise

    # Private helper methods

    def _generate_slug(self, name: str) -> str:
        """Generate URL-safe slug from name"""
        slug = name.lower().replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        return slug[:100]

    def _parse_label(self, label: str) -> Tuple[str, Optional[str]]:
        """Parse label into name and value (e.g., 'env:prod' → ('env', 'prod'))"""
        if ":" in label:
            parts = label.split(":", 1)
            return parts[0].strip(), parts[1].strip()
        return label.strip(), None

    def _generate_search_tokens(self, name: str, category: str, content: Dict[str, Any]) -> str:
        """Generate search tokens from playbook metadata"""
        tokens = [name.lower(), category.lower()]

        # Extract text from content
        content_str = json.dumps(content).lower()
        tokens.append(content_str[:500])  # First 500 chars

        return " ".join(tokens)

    async def _add_labels_to_playbook(
        self,
        playbook_id: int,
        labels: List[str],
        created_by: Optional[int] = None
    ):
        """Add labels to playbook in database"""
        with self.db.get_connection() as conn:
            for label in labels:
                label_name, label_value = self._parse_label(label)
                try:
                    conn.execute("""
                        INSERT INTO playbook_labels
                        (playbook_id, label_name, label_value, label_type, created_by, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (playbook_id, label_name, label_value, 'user', created_by, datetime.now()))
                except Exception:
                    # Label already exists (unique constraint)
                    pass
            conn.commit()

    async def _get_playbook_labels(self, playbook_id: int) -> List[str]:
        """Get all labels for a playbook"""
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT label_name, label_value
                FROM playbook_labels
                WHERE playbook_id = ?
                ORDER BY created_at ASC
            """, (playbook_id,))
            rows = cursor.fetchall()

            labels = []
            for row in rows:
                if row[1]:  # Has value
                    labels.append(f"{row[0]}:{row[1]}")
                else:
                    labels.append(row[0])

            return labels

    async def _index_playbook_in_chroma(
        self,
        playbook_id: int,
        name: str,
        content: Dict[str, Any],
        category: str,
        labels: List[str]
    ):
        """Index playbook in ChromaDB for semantic search"""
        if not self.playbook_collection or not self.embedding_model:
            return

        try:
            # Generate text for embedding
            text_for_embedding = f"{name}\n{category}\n"
            text_for_embedding += json.dumps(content, indent=2)[:1000]

            # Generate embedding
            embedding = self.embedding_model.encode([text_for_embedding])[0].tolist()

            # Store in ChromaDB
            self.playbook_collection.add(
                ids=[str(playbook_id)],
                embeddings=[embedding],
                documents=[text_for_embedding],
                metadatas=[{
                    "playbook_id": playbook_id,
                    "name": name,
                    "category": category,
                    "labels": ",".join(labels)
                }]
            )

            logger.debug(f"Indexed playbook {playbook_id} in ChromaDB")

        except Exception as e:
            logger.error(f"Error indexing playbook in ChromaDB: {e}")

    async def _semantic_search(
        self,
        query: str,
        labels: Optional[List[str]],
        category: Optional[str],
        similarity_threshold: float,
        match_all_labels: bool,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using ChromaDB"""
        if not self.playbook_collection or not self.embedding_model:
            return []

        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0].tolist()

            # Build where filter
            where_filter = {}
            if category:
                where_filter["category"] = category

            # Query ChromaDB
            results = self.playbook_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit * 2,  # Get more to allow for label filtering
                where=where_filter if where_filter else None
            )

            # Filter by labels if provided
            playbooks = []
            for idx, (doc_id, metadata, distance) in enumerate(zip(
                results['ids'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                similarity = 1 - distance  # Convert distance to similarity

                if similarity < similarity_threshold:
                    continue

                playbook_id = int(doc_id)
                playbook_labels = metadata.get('labels', '').split(',') if metadata.get('labels') else []

                # Apply label filtering
                if labels:
                    if match_all_labels:
                        # AND logic: must have all labels
                        if not all(label in playbook_labels for label in labels):
                            continue
                    else:
                        # OR logic: must have at least one label
                        if not any(label in playbook_labels for label in labels):
                            continue

                # Get full playbook data
                playbook = await self.get_playbook(playbook_id=playbook_id)
                if playbook:
                    playbook['similarity_score'] = round(similarity, 3)
                    playbooks.append(playbook)

                if len(playbooks) >= limit:
                    break

            return playbooks

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    async def _fulltext_search(
        self,
        query: str,
        labels: Optional[List[str]],
        category: Optional[str],
        match_all_labels: bool,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform full-text search using SQLite"""
        try:
            with self.db.get_connection() as conn:
                # Build query
                sql_parts = ["SELECT DISTINCT p.* FROM playbooks p"]
                where_clauses = []
                params = []

                # Join with labels if needed
                if labels:
                    sql_parts.append("LEFT JOIN playbook_labels pl ON p.id = pl.playbook_id")

                # Add where clauses
                if query:
                    where_clauses.append("(p.name LIKE ? OR p.search_tokens LIKE ?)")
                    query_pattern = f"%{query}%"
                    params.extend([query_pattern, query_pattern])

                if category:
                    where_clauses.append("p.category = ?")
                    params.append(category)

                if labels:
                    if match_all_labels:
                        # AND logic: subquery for each label
                        for label in labels:
                            label_name, label_value = self._parse_label(label)
                            if label_value:
                                where_clauses.append(
                                    "EXISTS (SELECT 1 FROM playbook_labels WHERE playbook_id = p.id AND label_name = ? AND label_value = ?)"
                                )
                                params.extend([label_name, label_value])
                            else:
                                where_clauses.append(
                                    "EXISTS (SELECT 1 FROM playbook_labels WHERE playbook_id = p.id AND label_name = ?)"
                                )
                                params.append(label_name)
                    else:
                        # OR logic: IN clause
                        label_conditions = []
                        for label in labels:
                            label_name, label_value = self._parse_label(label)
                            if label_value:
                                label_conditions.append("(pl.label_name = ? AND pl.label_value = ?)")
                                params.extend([label_name, label_value])
                            else:
                                label_conditions.append("pl.label_name = ?")
                                params.append(label_name)

                        if label_conditions:
                            where_clauses.append(f"({' OR '.join(label_conditions)})")

                # Build final query
                if where_clauses:
                    sql_parts.append("WHERE " + " AND ".join(where_clauses))

                sql_parts.append("ORDER BY p.updated_at DESC")
                sql_parts.append("LIMIT ?")
                params.append(limit)

                query_sql = " ".join(sql_parts)
                cursor = conn.execute(query_sql, params)
                rows = cursor.fetchall()

                # Convert to playbook dictionaries
                playbooks = []
                for row in rows:
                    playbook = self._row_to_playbook_dict(row)
                    playbook['labels'] = await self._get_playbook_labels(playbook['id'])
                    playbooks.append(playbook)

                return playbooks

        except Exception as e:
            logger.error(f"Error in full-text search: {e}")
            return []

    def _row_to_playbook_dict(self, row) -> Dict[str, Any]:
        """Convert database row to playbook dictionary"""
        return {
            "id": row[0],
            "name": row[1],
            "slug": row[2],
            "category": row[3],
            "format": row[5],
            "content": json.loads(row[6]) if row[6] else {},
            "created_by": row[10],
            "created_at": row[11],
            "updated_at": row[12]
        }

    async def _update_chroma_labels(
        self,
        playbook_id: int,
        labels: List[str],
        operation: str = "add"
    ):
        """Update ChromaDB metadata when labels change"""
        if not self.playbook_collection:
            return

        try:
            # Get current metadata
            result = self.playbook_collection.get(ids=[str(playbook_id)])
            if not result['metadatas']:
                return

            metadata = result['metadatas'][0]
            current_labels = set(metadata.get('labels', '').split(',')) if metadata.get('labels') else set()

            # Update labels
            if operation == "add":
                current_labels.update(labels)
            elif operation == "remove":
                current_labels.difference_update(labels)

            # Update ChromaDB
            metadata['labels'] = ','.join(sorted(current_labels))
            self.playbook_collection.update(
                ids=[str(playbook_id)],
                metadatas=[metadata]
            )

            logger.debug(f"Updated ChromaDB labels for playbook {playbook_id}")

        except Exception as e:
            logger.error(f"Error updating ChromaDB labels: {e}")

    async def _invalidate_cache(self, playbook_id: int):
        """Invalidate Redis cache for playbook"""
        if not self.redis_client:
            return

        try:
            # Delete cache keys
            patterns = [
                f"playbook:{playbook_id}",
                f"playbook:*"  # Invalidate search results cache (if implemented)
            ]

            for pattern in patterns:
                if "*" in pattern:
                    # Scan and delete matching keys
                    cursor = 0
                    while True:
                        cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)
                        if keys:
                            await self.redis_client.delete(*keys)
                        if cursor == 0:
                            break
                else:
                    await self.redis_client.delete(pattern)

            logger.debug(f"Invalidated cache for playbook {playbook_id}")

        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
