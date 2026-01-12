#!/usr/bin/env python3
"""
HiveSink Init - Simple file-based vault sync for hAIveMind.

Provides bi-directional sync for skills, docs, and configs between
local project and hAIveMind vault storage.
"""

import os
import json
import shutil
import hashlib
import difflib
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum


# Token threshold - approximately 4 chars per token
# 8000 tokens ~= 32KB, but we'll be conservative at 6000 tokens ~= 24KB
MAX_OUTPUT_TOKENS = 6000
CHARS_PER_TOKEN = 4
MAX_OUTPUT_CHARS = MAX_OUTPUT_TOKENS * CHARS_PER_TOKEN


@dataclass
class OutputResult:
    """Result that may be truncated with full output in a file."""
    content: str
    truncated: bool = False
    output_file: Optional[str] = None
    original_size: int = 0
    token_estimate: int = 0

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "truncated": self.truncated,
            "output_file": self.output_file,
            "original_size": self.original_size,
            "token_estimate": self.token_estimate,
        }


class OutputManager:
    """
    Manages output size to prevent token overflow.

    If output exceeds MAX_OUTPUT_CHARS, saves full content to /tmp
    and returns a truncated version with file path.
    """

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough estimate of tokens (4 chars per token)."""
        return len(text) // CHARS_PER_TOKEN

    @staticmethod
    def process_output(
        content: Union[str, dict],
        prefix: str = "hivesink",
        summary_generator: Optional[Callable[[str], str]] = None,
    ) -> OutputResult:
        """
        Process output, saving to file if too large.

        Args:
            content: The content to output (string or dict to JSON)
            prefix: Prefix for temp file name
            summary_generator: Optional function to generate summary from content

        Returns:
            OutputResult with content (possibly truncated) and file path if saved
        """
        # Convert dict to JSON string
        if isinstance(content, dict):
            text = json.dumps(content, indent=2)
        else:
            text = str(content)

        original_size = len(text)
        token_estimate = OutputManager.estimate_tokens(text)

        # If within limits, return as-is
        if original_size <= MAX_OUTPUT_CHARS:
            return OutputResult(
                content=text,
                truncated=False,
                original_size=original_size,
                token_estimate=token_estimate,
            )

        # Save to temp file with secure permissions (owner read/write only)
        fd, temp_path = tempfile.mkstemp(prefix=f"{prefix}_", suffix=".txt", text=True)
        try:
            os.chmod(temp_path, 0o600)  # rw------- (owner only)
            with os.fdopen(fd, 'w') as f:
                f.write(text)
        except Exception:
            os.close(fd)
            raise
        temp_file = Path(temp_path)

        # Generate summary
        if summary_generator:
            summary = summary_generator(content if isinstance(content, dict) else text)
        else:
            summary = OutputManager._default_summary(text, original_size, token_estimate)

        return OutputResult(
            content=summary,
            truncated=True,
            output_file=str(temp_file),
            original_size=original_size,
            token_estimate=token_estimate,
        )

    @staticmethod
    def _default_summary(text: str, size: int, tokens: int) -> str:
        """Generate default summary for truncated output."""
        # Show first 1000 chars as preview
        preview = text[:1000]
        if len(text) > 1000:
            preview += "\n...\n"

        return f"""Output too large for context ({tokens:,} tokens, {size:,} chars).

Preview:
{preview}

Full output saved to file (see output_file path)."""

    @staticmethod
    def format_sync_summary(preview: dict) -> str:
        """Generate a summary for sync preview results."""
        new_count = len(preview.get("new", []))
        changed_count = len(preview.get("changed", []))
        unchanged_count = len(preview.get("unchanged", []))

        summary_lines = [
            f"Sync Preview Summary:",
            f"  New files:       {new_count}",
            f"  Changed files:   {changed_count}",
            f"  Unchanged files: {unchanged_count}",
            "",
        ]

        # List files without full diffs
        if preview.get("new"):
            summary_lines.append("New files:")
            for item in preview["new"]:
                summary_lines.append(f"  + {item['file']} ({item['type']})")

        if preview.get("changed"):
            summary_lines.append("\nChanged files (diffs in output file):")
            for item in preview["changed"]:
                summary_lines.append(f"  ~ {item['file']} ({item['type']})")

        summary_lines.append("\nFull output with diffs saved to file (see output_file path).")

        return "\n".join(summary_lines)


class SyncDirection(Enum):
    DOWN = "down"  # Pull from vault to local
    UP = "up"      # Push from local to vault


class SyncScope(Enum):
    PERSONAL = "personal"  # ~/.haivemind/vault/
    TEAM = "team"          # ~/.haivemind/team/<name>/
    GLOBAL = "global"      # hAIveMind MCP sync


class ContentType(Enum):
    SKILLS = "skills"
    DOCS = "docs"
    CONFIGS = "configs"


@dataclass
class FileInfo:
    """Information about a file in the vault or local."""
    path: str
    hash: str
    modified: str
    size: int
    version: Optional[str] = None


@dataclass
class ReleaseInfo:
    """Information about a release."""
    version: str
    release_date: str
    files: Dict[str, Dict[str, Any]]  # filename -> {version, hash, changelog}
    changelog: str = ""
    min_compatible_version: str = "1.0.0"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ReleaseInfo':
        return cls(**data)


@dataclass
class UpdateInfo:
    """Information about available updates."""
    has_updates: bool
    current_version: str
    latest_version: str
    updates_available: List[Dict[str, Any]]  # [{file, current_ver, new_ver, changelog}]
    release_date: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VaultManifest:
    """Manifest tracking vault contents."""
    version: str = "1.0"
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    updated: str = field(default_factory=lambda: datetime.now().isoformat())
    scope: str = "personal"
    files: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'VaultManifest':
        return cls(**data)


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    direction: str
    scope: str
    synced: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    new: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False


class HiveSinkInit:
    """
    Simple file-based vault sync for hAIveMind.

    Vault locations by scope:
    - personal: ~/.haivemind/vault/
    - team: ~/.haivemind/team/<team_name>/
    - global: Uses hAIveMind MCP sync service
    """

    # File mappings: content_type -> [(local_pattern, vault_subdir)]
    FILE_MAPPINGS = {
        ContentType.SKILLS: [
            (".claude/commands/*.md", "skills"),
        ],
        ContentType.DOCS: [
            ("CLAUDE.md", "docs"),
            ("AGENT.md", "docs"),
        ],
        ContentType.CONFIGS: [
            (".mcp.json", "configs"),
            ("config/*.json", "configs"),
            ("sync-protocol.json", "configs"),
        ],
    }

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize HiveSink.

        Args:
            project_root: Root directory of the project. Defaults to cwd.
        """
        self.project_root = Path(project_root or os.getcwd())
        self.home = Path.home()
        self.haivemind_root = self.home / ".haivemind"

    def get_vault_path(self, scope: SyncScope, team_name: Optional[str] = None) -> Path:
        """Get the vault path for a given scope."""
        if scope == SyncScope.PERSONAL:
            return self.haivemind_root / "vault"
        elif scope == SyncScope.TEAM:
            if not team_name:
                raise ValueError("Team name required for team scope")
            return self.haivemind_root / "team" / team_name
        else:  # GLOBAL
            # For global, we'd use MCP sync - return a marker path
            return self.haivemind_root / "global"

    def ensure_vault_exists(self, vault_path: Path) -> None:
        """Create vault directory structure if it doesn't exist."""
        for subdir in ["skills", "docs", "configs"]:
            (vault_path / subdir).mkdir(parents=True, exist_ok=True)

        manifest_path = vault_path / "manifest.json"
        if not manifest_path.exists():
            manifest = VaultManifest()
            self._save_manifest(manifest, manifest_path)

    def _load_manifest(self, vault_path: Path) -> VaultManifest:
        """Load vault manifest."""
        manifest_path = vault_path / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                return VaultManifest.from_dict(json.load(f))
        return VaultManifest()

    def _save_manifest(self, manifest: VaultManifest, path: Path) -> None:
        """Save vault manifest."""
        manifest.updated = datetime.now().isoformat()
        with open(path, 'w') as f:
            json.dump(manifest.to_dict(), f, indent=2)

    def _compute_hash(self, file_path: Path) -> str:
        """Compute MD5 hash of file contents for comparison purposes.

        Note: MD5 is used here for fast content comparison to detect file changes,
        not for cryptographic security. For this use case, collision resistance
        is not a concern as we're comparing known files, not verifying integrity
        against malicious tampering.
        """
        if not file_path.exists():
            return ""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def _get_file_info(self, file_path: Path) -> Optional[FileInfo]:
        """Get information about a file."""
        if not file_path.exists():
            return None

        stat = file_path.stat()
        return FileInfo(
            path=str(file_path),
            hash=self._compute_hash(file_path),
            modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            size=stat.st_size,
        )

    def _get_diff(self, file1: Path, file2: Path, max_size: int = 10_000_000) -> str:
        """Get unified diff between two files.

        Args:
            file1: First file path
            file2: Second file path
            max_size: Maximum file size in bytes to diff (default 10MB)
        """
        # Check file sizes before loading into memory
        size1 = file1.stat().st_size if file1.exists() else 0
        size2 = file2.stat().st_size if file2.exists() else 0

        if size1 > max_size or size2 > max_size:
            return f"[Files too large to diff: {size1:,} and {size2:,} bytes (max: {max_size:,})]"

        if not file1.exists():
            content1 = []
            label1 = "(does not exist)"
        else:
            content1 = file1.read_text().splitlines(keepends=True)
            label1 = str(file1)

        if not file2.exists():
            content2 = []
            label2 = "(does not exist)"
        else:
            content2 = file2.read_text().splitlines(keepends=True)
            label2 = str(file2)

        diff = difflib.unified_diff(
            content1, content2,
            fromfile=label1,
            tofile=label2,
            lineterm=''
        )
        return '\n'.join(diff)

    def _find_local_files(self, content_types: List[ContentType]) -> Dict[ContentType, List[Path]]:
        """Find local files matching the given content types."""
        result = {}

        for ctype in content_types:
            files = []
            for pattern, _ in self.FILE_MAPPINGS[ctype]:
                # Handle glob patterns
                if '*' in pattern:
                    files.extend(self.project_root.glob(pattern))
                else:
                    file_path = self.project_root / pattern
                    if file_path.exists():
                        files.append(file_path)
            result[ctype] = files

        return result

    def _find_vault_files(self, vault_path: Path, content_types: List[ContentType]) -> Dict[ContentType, List[Path]]:
        """Find files in vault matching the given content types."""
        result = {}

        for ctype in content_types:
            files = []
            # Get the vault subdirectory for this content type
            _, vault_subdir = self.FILE_MAPPINGS[ctype][0]
            vault_dir = vault_path / vault_subdir

            if vault_dir.exists():
                # Get all files in the vault subdirectory
                if ctype == ContentType.SKILLS:
                    files = list(vault_dir.glob("*.md"))
                elif ctype == ContentType.DOCS:
                    for name in ["CLAUDE.md", "AGENT.md"]:
                        path = vault_dir / name
                        if path.exists():
                            files.append(path)
                elif ctype == ContentType.CONFIGS:
                    files = list(vault_dir.glob("*.json"))
                    # Also check for mcp.json
                    mcp = vault_dir / "mcp.json"
                    if mcp.exists() and mcp not in files:
                        files.append(mcp)

            result[ctype] = files

        return result

    def _get_local_dest(self, vault_file: Path, content_type: ContentType) -> Path:
        """Get local destination path for a vault file."""
        filename = vault_file.name

        if content_type == ContentType.SKILLS:
            return self.project_root / ".claude" / "commands" / filename
        elif content_type == ContentType.DOCS:
            return self.project_root / filename
        elif content_type == ContentType.CONFIGS:
            if filename == "mcp.json":
                return self.project_root / ".mcp.json"
            elif filename == "sync-protocol.json":
                return self.project_root / filename
            else:
                return self.project_root / "config" / filename

        return self.project_root / filename

    def _get_vault_dest(self, local_file: Path, content_type: ContentType, vault_path: Path) -> Path:
        """Get vault destination path for a local file."""
        filename = local_file.name
        _, vault_subdir = self.FILE_MAPPINGS[content_type][0]

        # Handle .mcp.json -> mcp.json rename
        if filename == ".mcp.json":
            filename = "mcp.json"

        # Security: Validate path doesn't escape vault directory
        dest = (vault_path / vault_subdir / filename).resolve()
        vault_resolved = vault_path.resolve()
        if not str(dest).startswith(str(vault_resolved) + "/") and dest != vault_resolved:
            raise ValueError(f"Path traversal detected: {filename} would escape vault directory")

        return dest

    def _sync_item(
        self,
        direction: SyncDirection,
        item: Dict[str, Any],
        vault_path: Path,
        content_types: List[ContentType],
        dry_run: bool,
    ) -> bool:
        """
        Sync a single item (file) in the given direction.

        Args:
            direction: DOWN (pull from vault) or UP (push to vault)
            item: Dict with 'file', 'type', 'dest' keys from preview
            vault_path: Path to the vault
            content_types: List of content types being synced
            dry_run: If True, don't make changes

        Returns:
            True if sync was performed (or would be in dry_run), False otherwise
        """
        filename = item["file"]

        if direction == SyncDirection.DOWN:
            ctype = ContentType(item["type"])
            vault_file = vault_path / self.FILE_MAPPINGS[ctype][0][1] / filename
            local_dest = Path(item["dest"])

            if not dry_run:
                self.sync_file(vault_file, local_dest)
            return True
        else:
            # UP direction - find the local file
            for ctype in content_types:
                local_files = self._find_local_files([ctype])
                for f in local_files.get(ctype, []):
                    if f.name == filename:
                        vault_dest = Path(item["dest"])
                        if not dry_run:
                            self.sync_file(f, vault_dest)
                        return True
            return False

    def list_available(self, scope: SyncScope, team_name: Optional[str] = None) -> Dict[str, Any]:
        """List what's available in the vault."""
        vault_path = self.get_vault_path(scope, team_name)

        if not vault_path.exists():
            return {
                "exists": False,
                "path": str(vault_path),
                "skills": 0,
                "docs": 0,
                "configs": 0,
            }

        vault_files = self._find_vault_files(
            vault_path,
            [ContentType.SKILLS, ContentType.DOCS, ContentType.CONFIGS]
        )

        return {
            "exists": True,
            "path": str(vault_path),
            "skills": len(vault_files.get(ContentType.SKILLS, [])),
            "docs": len(vault_files.get(ContentType.DOCS, [])),
            "configs": len(vault_files.get(ContentType.CONFIGS, [])),
            "skill_names": [f.name for f in vault_files.get(ContentType.SKILLS, [])],
            "doc_names": [f.name for f in vault_files.get(ContentType.DOCS, [])],
            "config_names": [f.name for f in vault_files.get(ContentType.CONFIGS, [])],
        }

    def list_local(self) -> Dict[str, Any]:
        """List what's available locally."""
        local_files = self._find_local_files(
            [ContentType.SKILLS, ContentType.DOCS, ContentType.CONFIGS]
        )

        return {
            "path": str(self.project_root),
            "skills": len(local_files.get(ContentType.SKILLS, [])),
            "docs": len(local_files.get(ContentType.DOCS, [])),
            "configs": len(local_files.get(ContentType.CONFIGS, [])),
            "skill_names": [f.name for f in local_files.get(ContentType.SKILLS, [])],
            "doc_names": [f.name for f in local_files.get(ContentType.DOCS, [])],
            "config_names": [f.name for f in local_files.get(ContentType.CONFIGS, [])],
        }

    # =====================================================================
    # Version and Release Management
    # =====================================================================

    def _extract_version(self, file_path: Path) -> Optional[str]:
        """
        Extract version from file frontmatter (for .md files) or content.

        Looks for:
        - YAML frontmatter: version: X.Y.Z
        - JSON files: "version": "X.Y.Z"
        """
        if not file_path.exists():
            return None

        try:
            content = file_path.read_text()

            # For markdown files, check YAML frontmatter
            if file_path.suffix == '.md':
                if content.startswith('---'):
                    end = content.find('---', 3)
                    if end != -1:
                        frontmatter = content[3:end]
                        for line in frontmatter.split('\n'):
                            if line.strip().startswith('version:'):
                                return line.split(':', 1)[1].strip().strip('"\'')

            # For JSON files
            elif file_path.suffix == '.json':
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and 'version' in data:
                        return str(data['version'])
                except json.JSONDecodeError:
                    pass

            return None
        except Exception:
            return None

    def _get_release_path(self, scope: SyncScope, team_name: Optional[str] = None) -> Path:
        """Get path to release.json for the vault."""
        vault_path = self.get_vault_path(scope, team_name)
        return vault_path / "release.json"

    def _load_release_info(self, scope: SyncScope, team_name: Optional[str] = None) -> Optional[ReleaseInfo]:
        """Load release information from vault."""
        release_path = self._get_release_path(scope, team_name)
        if not release_path.exists():
            return None

        try:
            with open(release_path) as f:
                data = json.load(f)
                return ReleaseInfo.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def _save_release_info(self, release: ReleaseInfo, scope: SyncScope, team_name: Optional[str] = None) -> None:
        """Save release information to vault."""
        release_path = self._get_release_path(scope, team_name)
        release_path.parent.mkdir(parents=True, exist_ok=True)
        with open(release_path, 'w') as f:
            json.dump(release.to_dict(), f, indent=2)

    def create_release(
        self,
        version: str,
        scope: SyncScope,
        changelog: str = "",
        team_name: Optional[str] = None,
    ) -> ReleaseInfo:
        """
        Create a new release from current vault contents.

        Args:
            version: Semantic version string (e.g., "1.2.0")
            scope: Vault scope
            changelog: Release notes/changelog
            team_name: Team name if scope is TEAM

        Returns:
            ReleaseInfo with all file versions and hashes
        """
        vault_path = self.get_vault_path(scope, team_name)

        if not vault_path.exists():
            raise ValueError(f"Vault not found at {vault_path}")

        # Gather file info
        files = {}
        vault_files = self._find_vault_files(
            vault_path,
            [ContentType.SKILLS, ContentType.DOCS, ContentType.CONFIGS]
        )

        for ctype, file_list in vault_files.items():
            for file_path in file_list:
                file_version = self._extract_version(file_path) or "1.0.0"
                files[file_path.name] = {
                    "version": file_version,
                    "hash": self._compute_hash(file_path),
                    "type": ctype.value,
                    "size": file_path.stat().st_size,
                }

        release = ReleaseInfo(
            version=version,
            release_date=datetime.now().isoformat(),
            files=files,
            changelog=changelog,
        )

        self._save_release_info(release, scope, team_name)
        return release

    def check_for_updates(
        self,
        scope: SyncScope,
        team_name: Optional[str] = None,
    ) -> UpdateInfo:
        """
        Check for available updates by comparing local files with vault release.

        Returns:
            UpdateInfo with list of available updates
        """
        release = self._load_release_info(scope, team_name)

        if not release:
            return UpdateInfo(
                has_updates=False,
                current_version="unknown",
                latest_version="unknown",
                updates_available=[],
                release_date="",
            )

        updates = []
        local_files = self._find_local_files(
            [ContentType.SKILLS, ContentType.DOCS, ContentType.CONFIGS]
        )

        # Check each local file against release
        for ctype, file_list in local_files.items():
            for local_file in file_list:
                filename = local_file.name
                if filename == ".mcp.json":
                    filename = "mcp.json"

                if filename in release.files:
                    local_version = self._extract_version(local_file) or "0.0.0"
                    release_version = release.files[filename].get("version", "1.0.0")
                    local_hash = self._compute_hash(local_file)
                    release_hash = release.files[filename].get("hash", "")

                    # Check if update available (different hash or version)
                    if local_hash != release_hash:
                        updates.append({
                            "file": filename,
                            "type": ctype.value,
                            "current_version": local_version,
                            "new_version": release_version,
                            "has_new_version": self._compare_versions(local_version, release_version) < 0,
                        })

        # Check for new files in release not present locally
        local_filenames = set()
        for file_list in local_files.values():
            for f in file_list:
                name = f.name
                if name == ".mcp.json":
                    name = "mcp.json"
                local_filenames.add(name)

        for filename, info in release.files.items():
            if filename not in local_filenames:
                updates.append({
                    "file": filename,
                    "type": info.get("type", "unknown"),
                    "current_version": "not installed",
                    "new_version": info.get("version", "1.0.0"),
                    "has_new_version": True,
                    "is_new": True,
                })

        # Get local manifest version
        manifest = self._load_manifest(self.get_vault_path(scope, team_name))
        current_version = manifest.version if manifest else "unknown"

        return UpdateInfo(
            has_updates=len(updates) > 0,
            current_version=current_version,
            latest_version=release.version,
            updates_available=updates,
            release_date=release.release_date,
        )

    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two semantic versions.

        Returns:
            -1 if v1 < v2, 0 if equal, 1 if v1 > v2
        """
        def parse_version(v: str) -> List[int]:
            try:
                parts = v.replace('-', '.').split('.')
                return [int(p) for p in parts[:3]]
            except (ValueError, AttributeError):
                return [0, 0, 0]

        p1 = parse_version(v1)
        p2 = parse_version(v2)

        for a, b in zip(p1, p2):
            if a < b:
                return -1
            if a > b:
                return 1
        return 0

    def upgrade(
        self,
        scope: SyncScope,
        team_name: Optional[str] = None,
        files: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> SyncResult:
        """
        Upgrade local files from vault release.

        Args:
            scope: Vault scope
            team_name: Team name if scope is TEAM
            files: Optional list of specific files to upgrade (None = all)
            dry_run: If True, don't make changes

        Returns:
            SyncResult with upgrade details
        """
        update_info = self.check_for_updates(scope, team_name)

        if not update_info.has_updates:
            return SyncResult(
                success=True,
                direction="upgrade",
                scope=scope.value,
                dry_run=dry_run,
            )

        # Filter to specific files if requested
        updates_to_apply = update_info.updates_available
        if files:
            updates_to_apply = [u for u in updates_to_apply if u["file"] in files]

        # Perform sync for updated files
        file_decisions = {u["file"]: "sync" for u in updates_to_apply}

        # Get content types for the files
        content_types = set()
        for update in updates_to_apply:
            try:
                content_types.add(ContentType(update["type"]))
            except ValueError:
                pass

        if not content_types:
            content_types = [ContentType.SKILLS, ContentType.DOCS, ContentType.CONFIGS]

        return self.sync(
            direction=SyncDirection.DOWN,
            scope=scope,
            content_types=list(content_types),
            team_name=team_name,
            dry_run=dry_run,
            file_decisions=file_decisions,
        )

    def format_update_check(self, update_info: UpdateInfo) -> str:
        """Format update check results for display."""
        if not update_info.has_updates:
            return f"✓ All files up to date (release {update_info.latest_version})"

        lines = [
            f"🔄 Updates available! (release {update_info.latest_version}, {update_info.release_date[:10]})",
            "",
        ]

        # Group by type
        by_type: Dict[str, List[Dict]] = {}
        for update in update_info.updates_available:
            t = update.get("type", "other")
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(update)

        for type_name, updates in by_type.items():
            lines.append(f"{type_name.upper()}:")
            for u in updates:
                if u.get("is_new"):
                    lines.append(f"  + {u['file']} (NEW v{u['new_version']})")
                elif u.get("has_new_version"):
                    lines.append(f"  ↑ {u['file']} ({u['current_version']} → {u['new_version']})")
                else:
                    lines.append(f"  ~ {u['file']} (modified)")
            lines.append("")

        lines.append(f"Run 'hivesink-init down --all' or '/hivesink upgrade' to update.")
        return "\n".join(lines)

    def preview_sync(
        self,
        direction: SyncDirection,
        scope: SyncScope,
        content_types: List[ContentType],
        team_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Preview what would be synced.

        Returns dict with 'new', 'changed', 'unchanged' lists.
        """
        vault_path = self.get_vault_path(scope, team_name)

        if direction == SyncDirection.DOWN:
            # Pulling from vault to local
            if not vault_path.exists():
                return {"error": f"Vault not found at {vault_path}"}

            vault_files = self._find_vault_files(vault_path, content_types)
            result = {"new": [], "changed": [], "unchanged": []}

            for ctype, files in vault_files.items():
                for vault_file in files:
                    local_dest = self._get_local_dest(vault_file, ctype)

                    if not local_dest.exists():
                        result["new"].append({
                            "file": vault_file.name,
                            "type": ctype.value,
                            "dest": str(local_dest),
                        })
                    elif self._compute_hash(vault_file) != self._compute_hash(local_dest):
                        result["changed"].append({
                            "file": vault_file.name,
                            "type": ctype.value,
                            "dest": str(local_dest),
                            "diff": self._get_diff(local_dest, vault_file),
                        })
                    else:
                        result["unchanged"].append({
                            "file": vault_file.name,
                            "type": ctype.value,
                        })

            return result

        else:  # UP
            # Pushing from local to vault
            local_files = self._find_local_files(content_types)
            result = {"new": [], "changed": [], "unchanged": []}

            for ctype, files in local_files.items():
                for local_file in files:
                    vault_dest = self._get_vault_dest(local_file, ctype, vault_path)

                    if not vault_dest.exists():
                        result["new"].append({
                            "file": local_file.name,
                            "type": ctype.value,
                            "dest": str(vault_dest),
                        })
                    elif self._compute_hash(local_file) != self._compute_hash(vault_dest):
                        result["changed"].append({
                            "file": local_file.name,
                            "type": ctype.value,
                            "dest": str(vault_dest),
                            "diff": self._get_diff(vault_dest, local_file),
                        })
                    else:
                        result["unchanged"].append({
                            "file": local_file.name,
                            "type": ctype.value,
                        })

            return result

    def preview_sync_managed(
        self,
        direction: SyncDirection,
        scope: SyncScope,
        content_types: List[ContentType],
        team_name: Optional[str] = None,
    ) -> OutputResult:
        """
        Preview sync with automatic output management.

        If output is too large, saves to temp file and returns summary.
        """
        preview = self.preview_sync(direction, scope, content_types, team_name)

        if "error" in preview:
            return OutputResult(content=json.dumps(preview, indent=2))

        # Use OutputManager to handle large outputs
        return OutputManager.process_output(
            preview,
            prefix="hivesink_preview",
            summary_generator=lambda p: OutputManager.format_sync_summary(p) if isinstance(p, dict) else None,
        )

    def get_diff_managed(self, file1: Path, file2: Path) -> OutputResult:
        """
        Get diff with automatic output management.

        If diff is too large, saves to temp file.
        """
        diff = self._get_diff(file1, file2)

        return OutputManager.process_output(
            diff,
            prefix=f"hivesink_diff_{file1.name}",
        )

    def sync_file(
        self,
        source: Path,
        dest: Path,
        dry_run: bool = False,
    ) -> bool:
        """
        Sync a single file from source to dest.

        Returns True if file was synced, False if skipped.
        """
        if dry_run:
            return True

        # Ensure destination directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(source, dest)
        return True

    def sync(
        self,
        direction: SyncDirection,
        scope: SyncScope,
        content_types: List[ContentType],
        team_name: Optional[str] = None,
        dry_run: bool = False,
        skip_unchanged: bool = True,
        file_decisions: Optional[Dict[str, str]] = None,  # filename -> "sync"|"skip"
    ) -> SyncResult:
        """
        Perform the sync operation.

        Args:
            direction: DOWN (pull) or UP (push)
            scope: PERSONAL, TEAM, or GLOBAL
            content_types: List of content types to sync
            team_name: Required if scope is TEAM
            dry_run: If True, don't make changes
            skip_unchanged: If True, skip files that haven't changed
            file_decisions: Dict mapping filenames to "sync" or "skip"

        Returns:
            SyncResult with details of what was synced
        """
        vault_path = self.get_vault_path(scope, team_name)
        file_decisions = file_decisions or {}

        result = SyncResult(
            success=True,
            direction=direction.value,
            scope=scope.value,
            dry_run=dry_run,
        )

        if direction == SyncDirection.UP:
            # Ensure vault exists for push
            if not dry_run:
                self.ensure_vault_exists(vault_path)
        else:
            # Check vault exists for pull
            if not vault_path.exists():
                result.success = False
                result.errors.append(f"Vault not found at {vault_path}")
                return result

        # Get preview to know what needs to be done
        preview = self.preview_sync(direction, scope, content_types, team_name)

        if "error" in preview:
            result.success = False
            result.errors.append(preview["error"])
            return result

        # Process new files (always sync)
        for item in preview["new"]:
            filename = item["file"]
            if file_decisions.get(filename) == "skip":
                result.skipped.append(filename)
                continue

            self._sync_item(direction, item, vault_path, content_types, dry_run)
            result.new.append(filename)

        # Process changed files (check decisions)
        for item in preview["changed"]:
            filename = item["file"]
            decision = file_decisions.get(filename, "sync")  # Default to sync

            if decision == "skip":
                result.skipped.append(filename)
                continue

            self._sync_item(direction, item, vault_path, content_types, dry_run)
            result.synced.append(filename)

        # Unchanged files
        for item in preview["unchanged"]:
            if skip_unchanged:
                result.skipped.append(item["file"])

        # Update manifest
        if not dry_run and direction == SyncDirection.UP:
            manifest = self._load_manifest(vault_path)
            for filename in result.synced + result.new:
                manifest.files[filename] = {
                    "synced": datetime.now().isoformat(),
                    "source": str(self.project_root),
                }
            self._save_manifest(manifest, vault_path / "manifest.json")

        return result


def check_updates_on_startup(
    scope: str = "personal",
    team_name: Optional[str] = None,
    quiet: bool = False,
) -> Optional[UpdateInfo]:
    """
    Check for updates on startup - designed to be called by memory_server.py.

    Args:
        scope: Vault scope (personal/team/global)
        team_name: Team name if scope is team
        quiet: If True, only return info, don't print

    Returns:
        UpdateInfo if updates available, None otherwise
    """
    try:
        hivesink = HiveSinkInit()
        sync_scope = SyncScope(scope)
        update_info = hivesink.check_for_updates(sync_scope, team_name)

        if update_info.has_updates and not quiet:
            print("\n" + "=" * 50)
            print("🔄 hAIveMind Updates Available!")
            print("=" * 50)
            print(hivesink.format_update_check(update_info))
            print("=" * 50 + "\n")

        return update_info if update_info.has_updates else None
    except Exception as e:
        if not quiet:
            print(f"⚠️  Could not check for updates: {e}")
        return None


def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="HiveSink Init - Vault Sync and Release Management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Common arguments
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--scope", choices=["personal", "team", "global"], default="personal")
    common_parser.add_argument("--team", help="Team name (required for team scope)")

    # Sync command (down/up)
    sync_parser = subparsers.add_parser("sync", parents=[common_parser], help="Sync files with vault")
    sync_parser.add_argument("direction", choices=["down", "up"], help="Sync direction")
    sync_parser.add_argument("--all", action="store_true", help="Sync all content types")
    sync_parser.add_argument("--skills", action="store_true", help="Sync skills only")
    sync_parser.add_argument("--docs", action="store_true", help="Sync docs only")
    sync_parser.add_argument("--configs", action="store_true", help="Sync configs only")
    sync_parser.add_argument("--dry-run", action="store_true", help="Preview without changes")

    # Check command (no additional args needed)
    subparsers.add_parser("check", parents=[common_parser], help="Check for available updates")

    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", parents=[common_parser], help="Upgrade to latest release")
    upgrade_parser.add_argument("--files", nargs="+", help="Specific files to upgrade")
    upgrade_parser.add_argument("--dry-run", action="store_true", help="Preview without changes")

    # Release command
    release_parser = subparsers.add_parser("release", parents=[common_parser], help="Create a new release")
    release_parser.add_argument("version", help="Version string (e.g., 1.2.0)")
    release_parser.add_argument("--changelog", "-m", default="", help="Release changelog/notes")

    # List command (no additional args needed)
    subparsers.add_parser("list", parents=[common_parser], help="List vault and local contents")

    # Legacy support: if first arg is down/up, treat as sync command
    import sys

    # Check if first arg is down/up (legacy mode) before parsing
    if len(sys.argv) > 1 and sys.argv[1] in ["down", "up"]:
        # Re-parse with legacy mode
        legacy_parser = argparse.ArgumentParser(description="HiveSink Init - Vault Sync")
        legacy_parser.add_argument("direction", choices=["down", "up"], help="Sync direction")
        legacy_parser.add_argument("--scope", choices=["personal", "team", "global"], default="personal")
        legacy_parser.add_argument("--team", help="Team name (required for team scope)")
        legacy_parser.add_argument("--all", action="store_true", help="Sync all content types")
        legacy_parser.add_argument("--skills", action="store_true", help="Sync skills only")
        legacy_parser.add_argument("--docs", action="store_true", help="Sync docs only")
        legacy_parser.add_argument("--configs", action="store_true", help="Sync configs only")
        legacy_parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
        legacy_parser.add_argument("--list", action="store_true", help="List available content")
        args = legacy_parser.parse_args()
        args.command = "sync"
    else:
        args = parser.parse_args()

        # Handle no command
        if args.command is None:
            parser.print_help()
            return

    hivesink = HiveSinkInit()
    scope = SyncScope(args.scope)

    if args.command == "list":
        print("Vault contents:")
        print(json.dumps(hivesink.list_available(scope, args.team), indent=2))
        print("\nLocal contents:")
        print(json.dumps(hivesink.list_local(), indent=2))

    elif args.command == "check":
        update_info = hivesink.check_for_updates(scope, args.team)
        print(hivesink.format_update_check(update_info))

    elif args.command == "upgrade":
        update_info = hivesink.check_for_updates(scope, args.team)
        if not update_info.has_updates:
            print("✓ All files up to date!")
            return

        print(hivesink.format_update_check(update_info))
        print()

        if args.dry_run:
            print("Dry run - no changes made.")
        else:
            result = hivesink.upgrade(scope, args.team, args.files, args.dry_run)
            print("\nUpgrade Result:")
            print(f"  Updated: {result.synced}")
            print(f"  New: {result.new}")
            print(f"  Skipped: {result.skipped}")
            if result.errors:
                print(f"  Errors: {result.errors}")

    elif args.command == "release":
        try:
            release = hivesink.create_release(args.version, scope, args.changelog, args.team)
            print(f"✓ Release {release.version} created!")
            print(f"  Files: {len(release.files)}")
            print(f"  Date: {release.release_date[:10]}")
            if release.changelog:
                print(f"  Changelog: {release.changelog}")
        except ValueError as e:
            print(f"❌ Error: {e}")

    elif args.command == "sync":
        # Handle --list flag for legacy mode
        if hasattr(args, 'list') and args.list:
            print("Vault contents:")
            print(json.dumps(hivesink.list_available(scope, args.team), indent=2))
            print("\nLocal contents:")
            print(json.dumps(hivesink.list_local(), indent=2))
            return

        # Determine content types
        if args.all or not (args.skills or args.docs or args.configs):
            content_types = [ContentType.SKILLS, ContentType.DOCS, ContentType.CONFIGS]
        else:
            content_types = []
            if args.skills:
                content_types.append(ContentType.SKILLS)
            if args.docs:
                content_types.append(ContentType.DOCS)
            if args.configs:
                content_types.append(ContentType.CONFIGS)

        direction = SyncDirection(args.direction)

        if args.dry_run:
            # Use managed output to handle large diffs
            output = hivesink.preview_sync_managed(direction, scope, content_types, args.team)
            print("Preview:")
            print(output.content)
            if output.truncated:
                print(f"\n📁 Full output saved to: {output.output_file}")
                print(f"   Size: {output.original_size:,} chars (~{output.token_estimate:,} tokens)")
        else:
            result = hivesink.sync(direction, scope, content_types, args.team)
            print("Result:")
            print(f"  Synced: {result.synced}")
            print(f"  New: {result.new}")
            print(f"  Skipped: {result.skipped}")
            if result.errors:
                print(f"  Errors: {result.errors}")


if __name__ == "__main__":
    main()
