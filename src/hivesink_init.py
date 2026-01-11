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
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum


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
        """Compute MD5 hash of file contents."""
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

    def _get_diff(self, file1: Path, file2: Path) -> str:
        """Get unified diff between two files."""
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

        return vault_path / vault_subdir / filename

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

            if direction == SyncDirection.DOWN:
                ctype = ContentType(item["type"])
                vault_file = vault_path / self.FILE_MAPPINGS[ctype][0][1] / filename
                local_dest = Path(item["dest"])

                if not dry_run:
                    self.sync_file(vault_file, local_dest)
            else:
                # Find the local file
                for ctype in content_types:
                    local_files = self._find_local_files([ctype])
                    for f in local_files.get(ctype, []):
                        if f.name == filename:
                            vault_dest = Path(item["dest"])
                            if not dry_run:
                                self.sync_file(f, vault_dest)
                            break

            result.new.append(filename)

        # Process changed files (check decisions)
        for item in preview["changed"]:
            filename = item["file"]
            decision = file_decisions.get(filename, "sync")  # Default to sync

            if decision == "skip":
                result.skipped.append(filename)
                continue

            if direction == SyncDirection.DOWN:
                ctype = ContentType(item["type"])
                vault_file = vault_path / self.FILE_MAPPINGS[ctype][0][1] / filename
                local_dest = Path(item["dest"])

                if not dry_run:
                    self.sync_file(vault_file, local_dest)
            else:
                # Find the local file
                for ctype in content_types:
                    local_files = self._find_local_files([ctype])
                    for f in local_files.get(ctype, []):
                        if f.name == filename:
                            vault_dest = Path(item["dest"])
                            if not dry_run:
                                self.sync_file(f, vault_dest)
                            break

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


def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="HiveSink Init - Vault Sync")
    parser.add_argument("direction", choices=["down", "up"], help="Sync direction")
    parser.add_argument("--scope", choices=["personal", "team", "global"], default="personal")
    parser.add_argument("--team", help="Team name (required for team scope)")
    parser.add_argument("--all", action="store_true", help="Sync all content types")
    parser.add_argument("--skills", action="store_true", help="Sync skills only")
    parser.add_argument("--docs", action="store_true", help="Sync docs only")
    parser.add_argument("--configs", action="store_true", help="Sync configs only")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--list", action="store_true", help="List available content")

    args = parser.parse_args()

    hivesink = HiveSinkInit()

    if args.list:
        scope = SyncScope(args.scope)
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
    scope = SyncScope(args.scope)

    if args.dry_run:
        preview = hivesink.preview_sync(direction, scope, content_types, args.team)
        print("Preview:")
        print(json.dumps(preview, indent=2))
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
