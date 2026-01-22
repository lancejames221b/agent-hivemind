"""
Skills.sh Integration for hAIveMind

Provides smart skill discovery and installation from skills.sh directory.
Integrates with existing CommandInstaller and HiveSinkInit systems.

skills.sh is an open ecosystem of reusable capabilities for AI agents.
Skills are installed via: npx skills add <owner/repo>

Author: Lance James, Unit 221B Inc
"""

import subprocess
import json
import os
import re
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SkillInfo:
    """Information about a skill from skills.sh"""
    skill_id: str  # owner/repo format
    name: str
    description: str
    installs: int
    source_url: str
    install_command: str


@dataclass
class InstalledSkill:
    """Information about a locally installed skill"""
    name: str
    path: str
    tool: str
    size: int
    installed_at: str


class SkillsShIntegration:
    """
    Integration with skills.sh skill directory.

    Provides methods for:
    - Searching the skills.sh directory
    - Installing skills via npx
    - Listing installed skills across tools
    - Syncing skills to hAIveMind vault for team distribution
    """

    SKILLS_SH_URL = "https://skills.sh"

    # Tool paths for skill installation
    TOOL_SKILL_PATHS = {
        "claude": ".claude/skills",
        "cursor": ".cursor/skills",
        "kilo": ".kilo/skills",
        "cline": ".cline/skills",
        "codex": ".codex/skills",
    }

    # Alternative command paths (some tools use commands instead of skills)
    TOOL_COMMAND_PATHS = {
        "claude": ".claude/commands",
        "cursor": ".cursor/commands",
        "kilo": ".kilo/commands",
        "cline": ".cline/commands",
        "codex": ".codex/commands",
    }

    def __init__(self, command_installer=None, hivesink=None, vault_client=None):
        """
        Initialize skills.sh integration.

        Args:
            command_installer: Optional CommandInstaller instance for cross-tool sync
            hivesink: Optional HiveSinkInit instance for vault sync
            vault_client: Optional vault HTTP client for remote operations
        """
        self.command_installer = command_installer
        self.hivesink = hivesink
        self.vault_client = vault_client
        self.home = Path.home()

    def search_skills(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search skills.sh directory for skills matching query.

        Note: skills.sh doesn't have a public API, so this uses npx skills search
        or falls back to suggesting the web interface.

        Args:
            query: Search term (e.g., "react", "security", "testing")
            limit: Maximum results to return

        Returns:
            List of skill info dictionaries
        """
        try:
            # Try using npx skills search if available
            result = subprocess.run(
                ["npx", "skills", "search", query],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout:
                # Parse output - format varies by skills CLI version
                skills = self._parse_search_output(result.stdout, limit)
                if skills:
                    return skills

        except subprocess.TimeoutExpired:
            logger.warning("Skills search timed out")
        except FileNotFoundError:
            logger.info("npx not found, skills search unavailable")
        except Exception as e:
            logger.warning(f"Skills search failed: {e}")

        # Fallback: return helpful guidance
        return [{
            "skill_id": "search_manually",
            "name": f"Search skills.sh for: {query}",
            "description": f"Visit {self.SKILLS_SH_URL} and search for '{query}'",
            "installs": 0,
            "source_url": f"{self.SKILLS_SH_URL}?q={query.replace(' ', '+')}",
            "install_command": "npx skills add <owner/repo>"
        }]

    def _parse_search_output(self, output: str, limit: int) -> List[Dict[str, Any]]:
        """Parse npx skills search output into structured data"""
        skills = []
        lines = output.strip().split('\n')

        for line in lines[:limit]:
            # Try to extract skill info from line
            # Format varies - common patterns:
            # owner/repo - description (N installs)
            match = re.match(r'(\S+/\S+)\s*[-–]\s*(.+?)(?:\s*\((\d+)\s*installs?\))?$', line)
            if match:
                skill_id = match.group(1)
                description = match.group(2).strip()
                installs = int(match.group(3)) if match.group(3) else 0

                skills.append({
                    "skill_id": skill_id,
                    "name": skill_id.split('/')[-1],
                    "description": description,
                    "installs": installs,
                    "source_url": f"https://github.com/{skill_id}",
                    "install_command": f"npx skills add {skill_id}"
                })

        return skills

    def install_skill(
        self,
        skill_id: str,
        target_tool: str = "claude"
    ) -> Dict[str, Any]:
        """
        Install a skill from skills.sh using npx.

        Args:
            skill_id: Skill identifier in owner/repo format (e.g., "vercel/next-learn")
            target_tool: Target tool for installation (claude, cursor, etc.)

        Returns:
            Dictionary with installation result
        """
        try:
            logger.info(f"Installing skill {skill_id} for {target_tool}")

            # Run npx skills add
            result = subprocess.run(
                ["npx", "skills", "add", skill_id],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.home)  # Run from home directory
            )

            success = result.returncode == 0

            # Find where the skill was installed
            skill_path = None
            if success:
                skill_path = self._find_installed_skill(skill_id, target_tool)

            return {
                "success": success,
                "skill_id": skill_id,
                "target_tool": target_tool,
                "skill_path": str(skill_path) if skill_path else None,
                "output": result.stdout,
                "error": result.stderr if not success else None,
                "installed_at": datetime.utcnow().isoformat()
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "skill_id": skill_id,
                "error": "Installation timed out after 120 seconds"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "skill_id": skill_id,
                "error": "npx not found. Install Node.js to use skills.sh"
            }
        except Exception as e:
            logger.error(f"Failed to install skill {skill_id}: {e}")
            return {
                "success": False,
                "skill_id": skill_id,
                "error": str(e)
            }

    def _find_installed_skill(self, skill_id: str, tool: str) -> Optional[Path]:
        """Find where a skill was installed after npx skills add"""
        skill_name = skill_id.split('/')[-1]

        # Check skill paths
        for path_type in [self.TOOL_SKILL_PATHS, self.TOOL_COMMAND_PATHS]:
            if tool in path_type:
                skill_dir = self.home / path_type[tool]
                if skill_dir.exists():
                    # Look for skill file (might be .md, .txt, or directory)
                    for ext in ['', '.md', '.txt']:
                        skill_path = skill_dir / f"{skill_name}{ext}"
                        if skill_path.exists():
                            return skill_path

                    # Check for partial matches
                    for item in skill_dir.iterdir():
                        if skill_name.lower() in item.name.lower():
                            return item

        return None

    def get_installed_skills(self, tool: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        List skills installed for specific tool(s).

        Args:
            tool: Specific tool to check (None = all tools)

        Returns:
            Dictionary mapping tool name to list of installed skills
        """
        result = {}
        tools = [tool] if tool else self.TOOL_SKILL_PATHS.keys()

        for t in tools:
            skills = []

            # Check skills directory
            if t in self.TOOL_SKILL_PATHS:
                skills_path = self.home / self.TOOL_SKILL_PATHS[t]
                if skills_path.exists():
                    for item in skills_path.iterdir():
                        if item.is_file() and not item.name.startswith('.'):
                            skills.append({
                                "name": item.name,
                                "path": str(item),
                                "tool": t,
                                "type": "skill",
                                "size": item.stat().st_size,
                                "modified": datetime.fromtimestamp(
                                    item.stat().st_mtime
                                ).isoformat()
                            })

            # Check commands directory
            if t in self.TOOL_COMMAND_PATHS:
                commands_path = self.home / self.TOOL_COMMAND_PATHS[t]
                if commands_path.exists():
                    for item in commands_path.iterdir():
                        if item.is_file() and not item.name.startswith('.'):
                            skills.append({
                                "name": item.name,
                                "path": str(item),
                                "tool": t,
                                "type": "command",
                                "size": item.stat().st_size,
                                "modified": datetime.fromtimestamp(
                                    item.stat().st_mtime
                                ).isoformat()
                            })

            if skills:
                result[t] = skills

        return result

    def sync_skill_to_haivemind(self, skill_path: str) -> Dict[str, Any]:
        """
        Sync an installed skill to hAIveMind vault for team distribution.

        Args:
            skill_path: Path to the skill file to sync

        Returns:
            Dictionary with sync result
        """
        path = Path(skill_path)
        if not path.exists():
            return {"success": False, "error": f"Skill not found: {skill_path}"}

        try:
            # Use hivesink if available
            if self.hivesink:
                # HiveSinkInit handles the sync
                result = self.hivesink.sync(
                    direction="up",
                    content_types=["skills"],
                    files=[str(path)]
                )
                return {
                    "success": True,
                    "skill_name": path.name,
                    "synced_to": "haivemind_vault",
                    "result": result
                }

            # Fallback: use vault HTTP client
            if self.vault_client:
                with open(path, 'r') as f:
                    content = f.read()

                # POST to vault endpoint
                response = self.vault_client.upload_skill(path.name, content)
                return {
                    "success": response.get("success", False),
                    "skill_name": path.name,
                    "synced_to": "haivemind_vault",
                    "response": response
                }

            return {
                "success": False,
                "error": "No sync mechanism available (hivesink or vault_client required)"
            }

        except Exception as e:
            logger.error(f"Failed to sync skill {skill_path}: {e}")
            return {"success": False, "error": str(e)}

    def get_vault_skills(self) -> List[Dict[str, Any]]:
        """
        Get list of skills available in hAIveMind vault.

        Returns:
            List of skill info from vault
        """
        try:
            if self.vault_client:
                return self.vault_client.list_skills()

            if self.hivesink:
                manifest = self.hivesink.get_manifest()
                return [
                    {"name": f["name"], "path": f["path"], "hash": f.get("hash")}
                    for f in manifest.get("files", [])
                    if f.get("category") == "skills"
                ]

            return []

        except Exception as e:
            logger.error(f"Failed to get vault skills: {e}")
            return []

    def recommend_skills(self, context: str) -> List[Dict[str, Any]]:
        """
        Recommend skills based on current context/task.

        Args:
            context: Description of current task or context

        Returns:
            List of recommended skills with relevance scores
        """
        # Extract keywords from context
        keywords = self._extract_keywords(context)

        recommendations = []
        for keyword in keywords[:3]:  # Top 3 keywords
            results = self.search_skills(keyword, limit=3)
            for skill in results:
                if skill.get("skill_id") != "search_manually":
                    skill["relevance_keyword"] = keyword
                    recommendations.append(skill)

        # Deduplicate by skill_id
        seen = set()
        unique_recommendations = []
        for skill in recommendations:
            if skill["skill_id"] not in seen:
                seen.add(skill["skill_id"])
                unique_recommendations.append(skill)

        return unique_recommendations[:5]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text for skill search"""
        # Common tech keywords to look for
        tech_keywords = [
            "react", "vue", "angular", "next", "typescript", "javascript",
            "python", "golang", "rust", "java", "kubernetes", "docker",
            "aws", "gcp", "azure", "terraform", "ansible", "security",
            "testing", "api", "database", "graphql", "rest", "frontend",
            "backend", "fullstack", "devops", "mlops", "ai", "ml"
        ]

        text_lower = text.lower()
        found = []

        for keyword in tech_keywords:
            if keyword in text_lower:
                found.append(keyword)

        # Also extract any word that looks like a technology name
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        for word in words:
            if word.lower() not in found and word[0].isupper():
                found.append(word.lower())

        return found[:5]


# Singleton instance
_skills_sh_integration: Optional[SkillsShIntegration] = None


def get_skills_sh_integration(
    command_installer=None,
    hivesink=None,
    vault_client=None
) -> SkillsShIntegration:
    """Get or create the SkillsShIntegration singleton"""
    global _skills_sh_integration
    if _skills_sh_integration is None:
        _skills_sh_integration = SkillsShIntegration(
            command_installer=command_installer,
            hivesink=hivesink,
            vault_client=vault_client
        )
    return _skills_sh_integration
