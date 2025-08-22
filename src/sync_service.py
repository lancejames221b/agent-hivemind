#!/usr/bin/env python3
"""
Memory Sync Service - REST API and WebSocket service for remote memory synchronization
Enables sharing Claude memory across multiple machines via Tailscale network
"""

import asyncio
import json
import logging
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import redis
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class MemoryCreate(BaseModel):
    content: str
    category: str = "general"
    context: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    user_id: str = "default"

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    category: Optional[str] = None
    context: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

class SyncRequest(BaseModel):
    machine_id: str
    memories: List[Dict[str, Any]]
    vector_clock: Dict[str, int]

class ConnectionManager:
    """Manages WebSocket connections for real-time sync"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.machine_subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, machine_id: str):
        await websocket.accept()
        self.active_connections[machine_id] = websocket
        logger.info(f"Machine {machine_id} connected via WebSocket")
    
    def disconnect(self, machine_id: str):
        if machine_id in self.active_connections:
            del self.active_connections[machine_id]
        if machine_id in self.machine_subscriptions:
            del self.machine_subscriptions[machine_id]
        logger.info(f"Machine {machine_id} disconnected")
    
    async def send_personal_message(self, message: str, machine_id: str):
        if machine_id in self.active_connections:
            try:
                await self.active_connections[machine_id].send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to {machine_id}: {e}")
                self.disconnect(machine_id)
    
    async def broadcast_sync_event(self, event_data: Dict[str, Any], exclude_machine: Optional[str] = None):
        """Broadcast sync events to all connected machines"""
        message = json.dumps({
            "type": "sync_event",
            "data": event_data,
            "timestamp": datetime.now().isoformat()
        })
        
        disconnected = []
        for machine_id, connection in self.active_connections.items():
            if machine_id != exclude_machine:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to {machine_id}: {e}")
                    disconnected.append(machine_id)
        
        # Clean up disconnected machines
        for machine_id in disconnected:
            self.disconnect(machine_id)

class MemorySyncService:
    """Service for synchronizing memories across machines"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.machine_id = self._get_machine_id()
        self.redis_client = None
        self.known_machines: Set[str] = set()
        self.vector_clock: Dict[str, int] = {self.machine_id: 0}
        
        # Initialize Redis
        self._init_redis()
        
        # Discover other machines via Tailscale
        if config.get('sync', {}).get('discovery', {}).get('tailscale_enabled'):
            asyncio.create_task(self._discover_machines())
    
    def _get_machine_id(self) -> str:
        """Get unique machine identifier"""
        try:
            # Try to get Tailscale hostname first
            result = subprocess.run(['tailscale', 'status', '--json'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                status = json.loads(result.stdout)
                return status.get('Self', {}).get('HostName', socket.gethostname())
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass
        
        return socket.gethostname()
    
    def _init_redis(self):
        """Initialize Redis connection for caching and pub/sub"""
        try:
            redis_config = self.config['storage']['redis']
            self.redis_client = redis.Redis(
                host=redis_config['host'],
                port=redis_config['port'],
                db=redis_config['db'],
                password=redis_config.get('password'),
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis connection established for sync service")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def _discover_machines(self):
        """Discover other machines running memory sync via Tailscale"""
        while True:
            try:
                result = subprocess.run(['tailscale', 'status', '--json'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    status = json.loads(result.stdout)
                    for peer_key, peer_info in status.get('Peer', {}).items():
                        hostname = peer_info.get('HostName', '')
                        if hostname and hostname != self.machine_id:
                            self.known_machines.add(hostname)
                
                logger.info(f"Discovered machines: {list(self.known_machines)}")
                
            except Exception as e:
                logger.error(f"Failed to discover machines: {e}")
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def sync_with_machine(self, target_machine: str, port: int = 8899) -> bool:
        """Sync memories with a specific machine"""
        try:
            # Get recent memories from local storage
            # This would integrate with the MemoryStorage class
            local_memories = await self._get_local_memories_for_sync()
            
            sync_data = SyncRequest(
                machine_id=self.machine_id,
                memories=local_memories,
                vector_clock=self.vector_clock
            )
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try Tailscale address first
                url = f"http://{target_machine}:{port}/api/sync"
                response = await client.post(url, json=sync_data.dict())
                
                if response.status_code == 200:
                    remote_data = response.json()
                    await self._process_sync_response(remote_data)
                    logger.info(f"Successfully synced with {target_machine}")
                    return True
                else:
                    logger.warning(f"Sync failed with {target_machine}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to sync with {target_machine}: {e}")
            return False
    
    async def _get_local_memories_for_sync(self) -> List[Dict[str, Any]]:
        """Get local memories that need to be synced"""
        try:
            # Import ChromaDB here to avoid circular imports
            import chromadb
            from chromadb.config import Settings
            
            # Connect to local ChromaDB
            chroma_config = self.config['storage']['chromadb']
            client = chromadb.PersistentClient(
                path=chroma_config['path'],
                settings=Settings(
                    anonymized_telemetry=chroma_config.get('anonymized_telemetry', False),
                    allow_reset=True
                )
            )
            
            memories = []
            categories = self.config['memory']['categories']
            
            # Get memories from each collection
            for category in categories:
                collection_name = f"{category}_memories"
                try:
                    collection = client.get_collection(collection_name)
                    
                    # Get all memories from this collection
                    results = collection.get(
                        limit=1000,  # Adjust based on needs
                        include=['documents', 'metadatas', 'embeddings']
                    )
                    
                    if results['documents']:
                        for i, doc in enumerate(results['documents']):
                            memory_data = {
                                'id': results['ids'][i],
                                'content': doc,
                                'category': category,
                                'metadata': results['metadatas'][i],
                                'embedding': results['embeddings'][i] if results.get('embeddings') else None
                            }
                            memories.append(memory_data)
                            
                except ValueError:
                    # Collection doesn't exist
                    continue
                except Exception as e:
                    logger.error(f"Failed to get memories from {collection_name}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(memories)} memories for sync")
            return memories
            
        except Exception as e:
            logger.error(f"Failed to get local memories for sync: {e}")
            return []
    
    async def _process_sync_response(self, remote_data: Dict[str, Any]):
        """Process sync response from remote machine"""
        remote_memories = remote_data.get('memories', [])
        remote_vector_clock = remote_data.get('vector_clock', {})
        
        # Update vector clock
        for machine, timestamp in remote_vector_clock.items():
            self.vector_clock[machine] = max(
                self.vector_clock.get(machine, 0), 
                timestamp
            )
        
        # Process remote memories and merge into local ChromaDB
        if remote_memories:
            await self._merge_remote_memories(remote_memories)
    
    async def _merge_remote_memories(self, remote_memories: List[Dict[str, Any]]):
        """Merge remote memories into local ChromaDB collections"""
        try:
            # Import ChromaDB here to avoid circular imports
            import chromadb
            from chromadb.config import Settings
            
            # Connect to local ChromaDB
            chroma_config = self.config['storage']['chromadb']
            client = chromadb.PersistentClient(
                path=chroma_config['path'],
                settings=Settings(
                    anonymized_telemetry=chroma_config.get('anonymized_telemetry', False),
                    allow_reset=True
                )
            )
            
            # Group memories by category
            memories_by_category = {}
            for memory in remote_memories:
                category = memory.get('category', 'global')
                if category not in memories_by_category:
                    memories_by_category[category] = []
                memories_by_category[category].append(memory)
            
            # Process each category
            for category, memories in memories_by_category.items():
                collection_name = f"{category}_memories"
                
                try:
                    # Get or create collection
                    try:
                        collection = client.get_collection(collection_name)
                    except ValueError:
                        collection = client.create_collection(
                            name=collection_name,
                            metadata={"category": category, "machine_id": self.machine_id}
                        )
                    
                    # Process memories for this category
                    documents = []
                    metadatas = []
                    ids = []
                    embeddings = []
                    
                    for memory in memories:
                        memory_id = memory['id']
                        
                        # Check if memory already exists (conflict resolution)
                        try:
                            existing = collection.get(ids=[memory_id])
                            if existing['documents']:
                                # Memory exists, check if we should update
                                existing_meta = existing['metadatas'][0]
                                remote_meta = memory['metadata']
                                
                                # Simple timestamp-based conflict resolution
                                existing_time = existing_meta.get('created_at', '')
                                remote_time = remote_meta.get('created_at', '')
                                
                                if remote_time > existing_time:
                                    # Remote is newer, update
                                    collection.update(
                                        ids=[memory_id],
                                        documents=[memory['content']],
                                        metadatas=[remote_meta]
                                    )
                                    logger.info(f"Updated existing memory {memory_id}")
                                continue
                                
                        except Exception:
                            # Memory doesn't exist, add it
                            pass
                        
                        # Add new memory
                        documents.append(memory['content'])
                        metadatas.append(memory['metadata'])
                        ids.append(memory_id)
                        
                        # Add embedding if available
                        if memory.get('embedding'):
                            embeddings.append(memory['embedding'])
                    
                    # Batch add new memories
                    if documents:
                        add_kwargs = {
                            'documents': documents,
                            'metadatas': metadatas,
                            'ids': ids
                        }
                        
                        # Only include embeddings if we have them for all documents
                        if embeddings and len(embeddings) == len(documents):
                            add_kwargs['embeddings'] = embeddings
                        
                        collection.add(**add_kwargs)
                        logger.info(f"Added {len(documents)} new memories to {collection_name}")
                
                except Exception as e:
                    logger.error(f"Failed to merge memories into {collection_name}: {e}")
                    continue
            
            logger.info(f"Successfully merged {len(remote_memories)} remote memories")
            
        except Exception as e:
            logger.error(f"Failed to merge remote memories: {e}")
    
    def increment_vector_clock(self):
        """Increment vector clock for this machine"""
        self.vector_clock[self.machine_id] = int(time.time())

# FastAPI app
app = FastAPI(title="Memory Sync Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables (in production, use dependency injection)
config = {}
sync_service = None
connection_manager = ConnectionManager()
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Simple token verification (expand for production)"""
    # In production, implement proper JWT verification
    return credentials.credentials == "your-api-token"

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    global config, sync_service
    
    config_path = "/home/lj/memory-mcp/config/config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    sync_service = MemorySyncService(config)
    logger.info("Memory Sync Service started")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "Memory Sync Service"}

@app.get("/api/status")
async def get_status():
    """Get service status and known machines"""
    return {
        "machine_id": sync_service.machine_id if sync_service else "unknown",
        "known_machines": list(sync_service.known_machines) if sync_service else [],
        "vector_clock": sync_service.vector_clock if sync_service else {},
        "connected_websockets": len(connection_manager.active_connections)
    }

@app.post("/api/sync")
async def handle_sync(sync_request: SyncRequest, _: str = Depends(verify_token)):
    """Handle sync request from another machine"""
    try:
        if not sync_service:
            raise HTTPException(status_code=500, detail="Sync service not initialized")
        
        # Process incoming sync request
        await sync_service._process_sync_response({
            "memories": sync_request.memories,
            "vector_clock": sync_request.vector_clock
        })
        
        # Get local memories to send back
        local_memories = await sync_service._get_local_memories_for_sync()
        
        # Broadcast sync event to connected WebSockets
        await connection_manager.broadcast_sync_event({
            "type": "external_sync",
            "from_machine": sync_request.machine_id,
            "memory_count": len(sync_request.memories)
        }, exclude_machine=sync_request.machine_id)
        
        return {
            "status": "success",
            "machine_id": sync_service.machine_id,
            "memories": local_memories,
            "vector_clock": sync_service.vector_clock
        }
        
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trigger-sync")
async def trigger_sync(_: str = Depends(verify_token)):
    """Manually trigger sync with all known machines"""
    if not sync_service:
        raise HTTPException(status_code=500, detail="Sync service not initialized")
    
    results = {}
    for machine in sync_service.known_machines:
        try:
            success = await sync_service.sync_with_machine(machine)
            results[machine] = "success" if success else "failed"
        except Exception as e:
            results[machine] = f"error: {str(e)}"
    
    return {"sync_results": results}

@app.websocket("/ws/{machine_id}")
async def websocket_endpoint(websocket: WebSocket, machine_id: str):
    """WebSocket endpoint for real-time sync notifications"""
    await connection_manager.connect(websocket, machine_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message.get("type") == "sync_request":
                # Handle real-time sync request
                await connection_manager.broadcast_sync_event({
                    "type": "sync_request",
                    "from_machine": machine_id
                }, exclude_machine=machine_id)
                
    except WebSocketDisconnect:
        connection_manager.disconnect(machine_id)
    except Exception as e:
        logger.error(f"WebSocket error for {machine_id}: {e}")
        connection_manager.disconnect(machine_id)

def main():
    """Run the sync service"""
    config_path = "/home/lj/memory-mcp/config/config.json"
    
    # Load config
    with open(config_path, 'r') as f:
        server_config = json.load(f)
    
    # Run server
    uvicorn.run(
        "sync_service:app",
        host=server_config['server']['host'],
        port=server_config['server']['port'],
        reload=server_config['server']['debug'],
        log_level="info"
    )

if __name__ == "__main__":
    main()