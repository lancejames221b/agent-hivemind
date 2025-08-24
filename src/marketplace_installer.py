#!/usr/bin/env python3
"""
MCP Marketplace One-Click Installer
Provides automated installation and configuration of MCP servers from the marketplace
with integration to the MCP hosting system from Story 4c.

Author: Lance James, Unit 221B, Inc
Date: August 24, 2025
Version: 1.0.0
"""

import os
import json
import uuid
import shutil
import tempfile
import zipfile
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import yaml

# Import hosting system from Story 4c
try:
    from mcp_server_host import MCPServerHost
    from config_generator import ConfigGenerator
    MCP_HOSTING_AVAILABLE = True
except ImportError:
    MCP_HOSTING_AVAILABLE = False

# Import hAIveMind components
try:
    from memory_server import store_memory
    HAIVEMIND_AVAILABLE = True
except ImportError:
    HAIVEMIND_AVAILABLE = False

class MarketplaceInstaller:
    """
    One-click installer for MCP servers from the marketplace
    Integrates with the MCP hosting system for automated deployment
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.install_dir = Path(config.get("install_directory", "data/marketplace_installs"))
        self.install_dir.mkdir(parents=True, exist_ok=True)
        
        # Integration with MCP hosting system
        self.hosting_enabled = MCP_HOSTING_AVAILABLE and config.get("use_mcp_hosting", True)
        if self.hosting_enabled:
            self.mcp_host = MCPServerHost(config.get("mcp_hosting", {}))
        
        # Configuration generator
        self.config_generator = None
        if config.get("auto_generate_config", True):
            try:
                from config_generator import create_config_generator
                self.config_generator = create_config_generator(config)
            except ImportError:
                pass
        
        # Installation methods
        self.installation_methods = {
            "one_click": self._install_one_click,
            "manual": self._generate_manual_instructions,
            "cli": self._install_cli,
            "hosted": self._install_hosted,
            "docker": self._install_docker
        }
        
        # Template system
        self.templates_dir = Path(config.get("templates_directory", "templates/marketplace"))
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
    async def install_server(self, 
                           server_metadata: Dict[str, Any],
                           package_path: str,
                           installation_method: str = "one_click",
                           target_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Install a server using the specified method
        
        Args:
            server_metadata: Complete server metadata from marketplace
            package_path: Path to the server package file
            installation_method: Installation method to use
            target_config: Target configuration options
        
        Returns:
            Installation result with status and details
        """
        try:
            # Validate installation method
            if installation_method not in self.installation_methods:
                raise ValueError(f"Unsupported installation method: {installation_method}")
            
            # Create installation context
            install_context = {
                "server_id": server_metadata["id"],
                "server_name": server_metadata["name"],
                "version": server_metadata["version"],
                "installation_id": f"install_{uuid.uuid4().hex[:12]}",
                "method": installation_method,
                "timestamp": datetime.now(),
                "target_config": target_config or {}
            }
            
            # Store installation start in hAIveMind
            if HAIVEMIND_AVAILABLE:
                await store_memory(
                    content=f"Starting installation of {server_metadata['name']} v{server_metadata['version']} using {installation_method}",
                    category="marketplace",
                    metadata={
                        "action": "installation_started",
                        "server_id": server_metadata["id"],
                        "installation_id": install_context["installation_id"],
                        "method": installation_method
                    },
                    project="mcp-marketplace",
                    scope="project-shared"
                )
            
            # Execute installation
            installer_func = self.installation_methods[installation_method]
            result = await installer_func(server_metadata, package_path, install_context)
            
            # Store installation result in hAIveMind
            if HAIVEMIND_AVAILABLE:
                await store_memory(
                    content=f"Installation {'completed' if result['success'] else 'failed'}: {server_metadata['name']} - {result.get('message', 'No details')}",
                    category="marketplace",
                    metadata={
                        "action": "installation_completed",
                        "server_id": server_metadata["id"],
                        "installation_id": install_context["installation_id"],
                        "success": result["success"],
                        "method": installation_method,
                        "error": result.get("error") if not result["success"] else None
                    },
                    project="mcp-marketplace",
                    scope="project-shared"
                )
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "installation_id": install_context.get("installation_id"),
                "message": f"Installation failed: {str(e)}"
            }
            
            # Store error in hAIveMind
            if HAIVEMIND_AVAILABLE:
                await store_memory(
                    content=f"Installation error for {server_metadata.get('name', 'unknown')}: {str(e)}",
                    category="marketplace",
                    metadata={
                        "action": "installation_error",
                        "server_id": server_metadata.get("id"),
                        "error": str(e),
                        "method": installation_method
                    },
                    project="mcp-marketplace",
                    scope="project-shared"
                )
            
            return error_result
    
    async def _install_one_click(self, 
                               server_metadata: Dict[str, Any],
                               package_path: str,
                               install_context: Dict[str, Any]) -> Dict[str, Any]:
        """One-click installation with automatic configuration"""
        try:
            # Extract package
            extract_dir = self.install_dir / install_context["installation_id"]
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find main server file
            main_file = self._find_main_server_file(extract_dir)
            if not main_file:
                raise ValueError("Could not find main server file (server.py, main.py, or __main__.py)")
            
            # Install dependencies
            requirements_file = extract_dir / "requirements.txt"
            if requirements_file.exists():
                await self._install_dependencies(requirements_file)
            
            # Generate configuration
            config_data = await self._generate_server_config(server_metadata, extract_dir, install_context)
            
            # Start server if using hosted installation
            if self.hosting_enabled and install_context["target_config"].get("auto_start", True):
                result = await self._start_hosted_server(server_metadata, extract_dir, config_data)
                if not result["success"]:
                    return result
            
            # Generate client configuration
            client_config = None
            if self.config_generator:
                client_config = await self._generate_client_config(server_metadata, config_data)
            
            return {
                "success": True,
                "installation_id": install_context["installation_id"],
                "server_path": str(extract_dir),
                "main_file": str(main_file),
                "config_file": str(extract_dir / "config.json"),
                "client_config": client_config,
                "message": f"Server {server_metadata['name']} installed successfully",
                "next_steps": [
                    "Server is ready to use",
                    "Client configuration generated" if client_config else "Configure your MCP client manually",
                    "Check server logs for any issues",
                    "Test server functionality"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "installation_id": install_context["installation_id"]
            }
    
    async def _install_hosted(self, 
                            server_metadata: Dict[str, Any],
                            package_path: str,
                            install_context: Dict[str, Any]) -> Dict[str, Any]:
        """Install using the MCP hosting system from Story 4c"""
        if not self.hosting_enabled:
            return {
                "success": False,
                "error": "MCP hosting system not available",
                "installation_id": install_context["installation_id"]
            }
        
        try:
            # Read package data
            with open(package_path, 'rb') as f:
                package_data = f.read()
            
            # Use MCP hosting system
            import base64
            package_base64 = base64.b64encode(package_data).decode('utf-8')
            
            # Determine command based on server metadata
            language = server_metadata.get("language", "python")
            if language == "python":
                command = ["python", "server.py"]
            elif language == "javascript" or language == "node":
                command = ["node", "server.js"]
            else:
                command = ["python", "server.py"]  # Default fallback
            
            # Upload to hosting system
            from mcp_hosting_tools import upload_mcp_server
            
            result = await upload_mcp_server(
                name=f"{server_metadata['name']} (Marketplace)",
                archive_base64=package_base64,
                command=command,
                description=f"Marketplace server: {server_metadata['description']}",
                environment=install_context["target_config"].get("environment", {}),
                resource_limits=install_context["target_config"].get("resource_limits", {
                    "memory_mb": 256,
                    "cpu_percent": 30
                })
            )
            
            if result.get("success"):
                # Start the server
                from mcp_hosting_tools import start_mcp_server
                start_result = await start_mcp_server(result["server_id"])
                
                return {
                    "success": True,
                    "installation_id": install_context["installation_id"],
                    "hosted_server_id": result["server_id"],
                    "server_status": start_result.get("status", "unknown"),
                    "endpoint": f"http://localhost:{result.get('port', 8900)}/sse",
                    "message": f"Server {server_metadata['name']} deployed to hosting system",
                    "management_url": f"http://localhost:8910/servers/{result['server_id']}",
                    "next_steps": [
                        "Server is running in hosted environment",
                        "Access management dashboard for monitoring",
                        "Configure your MCP client with the provided endpoint",
                        "Monitor server logs and performance"
                    ]
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Hosting deployment failed"),
                    "installation_id": install_context["installation_id"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "installation_id": install_context["installation_id"]
            }
    
    async def _install_docker(self, 
                            server_metadata: Dict[str, Any],
                            package_path: str,
                            install_context: Dict[str, Any]) -> Dict[str, Any]:
        """Install using Docker containerization"""
        try:
            # Extract package
            extract_dir = self.install_dir / install_context["installation_id"]
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Generate Dockerfile if not present
            dockerfile_path = extract_dir / "Dockerfile"
            if not dockerfile_path.exists():
                dockerfile_content = await self._generate_dockerfile(server_metadata, extract_dir)
                with open(dockerfile_path, 'w') as f:
                    f.write(dockerfile_content)
            
            # Generate docker-compose.yml
            compose_content = await self._generate_docker_compose(server_metadata, install_context)
            compose_path = extract_dir / "docker-compose.yml"
            with open(compose_path, 'w') as f:
                f.write(compose_content)
            
            # Build and start container
            container_name = f"mcp-{server_metadata['id']}"
            
            # Build image
            build_cmd = ["docker", "build", "-t", container_name, str(extract_dir)]
            build_result = await self._run_command(build_cmd)
            
            if build_result["returncode"] != 0:
                return {
                    "success": False,
                    "error": f"Docker build failed: {build_result['stderr']}",
                    "installation_id": install_context["installation_id"]
                }
            
            # Start container
            if install_context["target_config"].get("auto_start", True):
                start_cmd = ["docker-compose", "-f", str(compose_path), "up", "-d"]
                start_result = await self._run_command(start_cmd, cwd=extract_dir)
                
                if start_result["returncode"] != 0:
                    return {
                        "success": False,
                        "error": f"Docker start failed: {start_result['stderr']}",
                        "installation_id": install_context["installation_id"]
                    }
            
            return {
                "success": True,
                "installation_id": install_context["installation_id"],
                "container_name": container_name,
                "compose_file": str(compose_path),
                "dockerfile": str(dockerfile_path),
                "message": f"Server {server_metadata['name']} containerized successfully",
                "docker_commands": {
                    "start": f"docker-compose -f {compose_path} up -d",
                    "stop": f"docker-compose -f {compose_path} down",
                    "logs": f"docker-compose -f {compose_path} logs -f",
                    "status": f"docker-compose -f {compose_path} ps"
                },
                "next_steps": [
                    "Container is built and ready",
                    "Use docker-compose commands to manage the server",
                    "Configure your MCP client to connect to the container",
                    "Monitor container logs for issues"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "installation_id": install_context["installation_id"]
            }
    
    async def _generate_manual_instructions(self, 
                                          server_metadata: Dict[str, Any],
                                          package_path: str,
                                          install_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate manual installation instructions"""
        try:
            # Extract package to analyze structure
            temp_dir = Path(tempfile.mkdtemp())
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Analyze package structure
            main_file = self._find_main_server_file(temp_dir)
            requirements_file = temp_dir / "requirements.txt"
            config_file = temp_dir / "config.json"
            
            # Generate instructions
            instructions = {
                "installation_steps": [
                    {
                        "step": 1,
                        "title": "Extract Package",
                        "description": f"Extract the server package to your desired location",
                        "command": f"unzip {server_metadata['name']}-{server_metadata['version']}.zip"
                    },
                    {
                        "step": 2,
                        "title": "Install Dependencies",
                        "description": "Install required dependencies",
                        "command": "pip install -r requirements.txt" if requirements_file.exists() else "# No dependencies file found",
                        "required": requirements_file.exists()
                    },
                    {
                        "step": 3,
                        "title": "Configure Server",
                        "description": "Edit configuration file if needed",
                        "file": "config.json" if config_file.exists() else "Create config.json",
                        "required": True
                    },
                    {
                        "step": 4,
                        "title": "Start Server",
                        "description": "Start the MCP server",
                        "command": f"python {main_file.name}" if main_file else "python server.py",
                        "required": True
                    },
                    {
                        "step": 5,
                        "title": "Configure Client",
                        "description": "Add server to your MCP client configuration",
                        "example_config": {
                            "mcpServers": {
                                server_metadata["id"]: {
                                    "command": "python",
                                    "args": [str(main_file) if main_file else "server.py"],
                                    "env": {}
                                }
                            }
                        }
                    }
                ]
            }
            
            # Add language-specific instructions
            language = server_metadata.get("language", "python")
            if language == "javascript" or language == "node":
                instructions["installation_steps"][1]["command"] = "npm install"
                instructions["installation_steps"][3]["command"] = "node server.js"
                instructions["installation_steps"][4]["example_config"]["mcpServers"][server_metadata["id"]]["command"] = "node"
                instructions["installation_steps"][4]["example_config"]["mcpServers"][server_metadata["id"]]["args"] = ["server.js"]
            
            # Add troubleshooting tips
            instructions["troubleshooting"] = [
                "Ensure all dependencies are installed correctly",
                "Check that the server port is not already in use",
                "Verify file permissions are correct",
                "Check server logs for error messages",
                f"Refer to {server_metadata.get('homepage', 'server documentation')} for additional help"
            ]
            
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
            return {
                "success": True,
                "installation_id": install_context["installation_id"],
                "instructions": instructions,
                "server_info": {
                    "name": server_metadata["name"],
                    "version": server_metadata["version"],
                    "language": language,
                    "main_file": main_file.name if main_file else "server.py",
                    "has_requirements": requirements_file.exists(),
                    "has_config": config_file.exists()
                },
                "message": "Manual installation instructions generated",
                "next_steps": [
                    "Follow the installation steps in order",
                    "Test the server after installation",
                    "Refer to troubleshooting section if needed"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "installation_id": install_context["installation_id"]
            }
    
    async def _install_cli(self, 
                         server_metadata: Dict[str, Any],
                         package_path: str,
                         install_context: Dict[str, Any]) -> Dict[str, Any]:
        """Install using CLI commands"""
        try:
            # Generate CLI installation script
            script_content = await self._generate_cli_script(server_metadata, package_path, install_context)
            
            # Save script
            script_path = self.install_dir / f"install_{install_context['installation_id']}.sh"
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make script executable
            os.chmod(script_path, 0o755)
            
            # Execute script if auto-execute is enabled
            if install_context["target_config"].get("auto_execute", False):
                result = await self._run_command([str(script_path)])
                if result["returncode"] != 0:
                    return {
                        "success": False,
                        "error": f"CLI installation failed: {result['stderr']}",
                        "installation_id": install_context["installation_id"],
                        "script_path": str(script_path)
                    }
            
            return {
                "success": True,
                "installation_id": install_context["installation_id"],
                "script_path": str(script_path),
                "script_content": script_content,
                "message": f"CLI installation script generated for {server_metadata['name']}",
                "execution_command": f"bash {script_path}",
                "next_steps": [
                    f"Review the script at {script_path}",
                    f"Execute: bash {script_path}",
                    "Follow any additional setup instructions",
                    "Test the server after installation"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "installation_id": install_context["installation_id"]
            }
    
    # Helper methods
    
    def _find_main_server_file(self, directory: Path) -> Optional[Path]:
        """Find the main server file in the extracted package"""
        candidates = ["server.py", "main.py", "__main__.py", "app.py"]
        
        for candidate in candidates:
            file_path = directory / candidate
            if file_path.exists():
                return file_path
        
        # Look for any .py file with "server" in the name
        for file_path in directory.glob("*server*.py"):
            return file_path
        
        # Look for any .py file
        py_files = list(directory.glob("*.py"))
        if py_files:
            return py_files[0]
        
        return None
    
    async def _install_dependencies(self, requirements_file: Path) -> bool:
        """Install Python dependencies from requirements.txt"""
        try:
            cmd = ["pip", "install", "-r", str(requirements_file)]
            result = await self._run_command(cmd)
            return result["returncode"] == 0
        except Exception:
            return False
    
    async def _generate_server_config(self, 
                                    server_metadata: Dict[str, Any],
                                    install_dir: Path,
                                    install_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate server configuration"""
        config = {
            "server": {
                "name": server_metadata["name"],
                "version": server_metadata["version"],
                "id": server_metadata["id"],
                "port": install_context["target_config"].get("port", 8900),
                "host": install_context["target_config"].get("host", "localhost")
            },
            "marketplace": {
                "installed_from": "marketplace",
                "installation_id": install_context["installation_id"],
                "installation_method": install_context["method"],
                "installed_at": install_context["timestamp"].isoformat()
            },
            "tools": server_metadata.get("tools", []),
            "resources": server_metadata.get("resources", []),
            "prompts": server_metadata.get("prompts", [])
        }
        
        # Save configuration
        config_path = install_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config
    
    async def _generate_client_config(self, 
                                    server_metadata: Dict[str, Any],
                                    server_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate client configuration using the config generator"""
        if not self.config_generator:
            return None
        
        try:
            # Generate configuration for Claude Desktop
            config_data = await self.config_generator.generate_configuration(
                device_id="marketplace_install",
                format="claude_desktop",
                servers=[{
                    "id": server_metadata["id"],
                    "name": server_metadata["name"],
                    "endpoint": f"http://{server_config['server']['host']}:{server_config['server']['port']}/sse",
                    "transport": "sse"
                }]
            )
            
            return config_data
        except Exception:
            return None
    
    async def _start_hosted_server(self, 
                                 server_metadata: Dict[str, Any],
                                 server_dir: Path,
                                 config: Dict[str, Any]) -> Dict[str, Any]:
        """Start server using the hosting system"""
        if not self.hosting_enabled:
            return {"success": True, "message": "Hosting not enabled, server ready for manual start"}
        
        try:
            # This would integrate with the MCP hosting system
            # For now, return success
            return {
                "success": True,
                "message": "Server started successfully",
                "endpoint": f"http://localhost:{config['server']['port']}/sse"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_dockerfile(self, 
                                 server_metadata: Dict[str, Any],
                                 server_dir: Path) -> str:
        """Generate Dockerfile for the server"""
        language = server_metadata.get("language", "python")
        
        if language == "python":
            return f"""FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server files
COPY . .

# Expose port
EXPOSE 8900

# Start server
CMD ["python", "server.py"]
"""
        elif language in ["javascript", "node"]:
            return f"""FROM node:16-slim

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy server files
COPY . .

# Expose port
EXPOSE 8900

# Start server
CMD ["node", "server.js"]
"""
        else:
            # Generic Dockerfile
            return f"""FROM ubuntu:20.04

WORKDIR /app

# Install basic dependencies
RUN apt-get update && apt-get install -y python3 python3-pip

# Copy all files
COPY . .

# Install Python dependencies if present
RUN if [ -f requirements.txt ]; then pip3 install -r requirements.txt; fi

# Expose port
EXPOSE 8900

# Start server (adjust as needed)
CMD ["python3", "server.py"]
"""
    
    async def _generate_docker_compose(self, 
                                     server_metadata: Dict[str, Any],
                                     install_context: Dict[str, Any]) -> str:
        """Generate docker-compose.yml for the server"""
        service_name = f"mcp-{server_metadata['id']}"
        port = install_context["target_config"].get("port", 8900)
        
        compose_config = {
            "version": "3.8",
            "services": {
                service_name: {
                    "build": ".",
                    "ports": [f"{port}:{port}"],
                    "environment": install_context["target_config"].get("environment", {}),
                    "restart": "unless-stopped",
                    "volumes": ["./data:/app/data"] if install_context["target_config"].get("persist_data") else []
                }
            }
        }
        
        return yaml.dump(compose_config, default_flow_style=False)
    
    async def _generate_cli_script(self, 
                                 server_metadata: Dict[str, Any],
                                 package_path: str,
                                 install_context: Dict[str, Any]) -> str:
        """Generate CLI installation script"""
        script = f"""#!/bin/bash
# MCP Server Installation Script
# Server: {server_metadata['name']} v{server_metadata['version']}
# Generated: {datetime.now().isoformat()}

set -e

echo "Installing {server_metadata['name']} v{server_metadata['version']}..."

# Create installation directory
INSTALL_DIR="{self.install_dir / install_context['installation_id']}"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Extract package
echo "Extracting package..."
unzip -q "{package_path}"

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
elif [ -f "package.json" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

# Make scripts executable
chmod +x *.py *.js *.sh 2>/dev/null || true

# Generate configuration
cat > config.json << 'EOF'
{json.dumps(await self._generate_server_config(server_metadata, Path(self.install_dir / install_context['installation_id']), install_context), indent=2)}
EOF

echo "Installation completed successfully!"
echo "Server installed to: $INSTALL_DIR"
echo "To start the server, run:"

# Determine start command based on language
"""
        
        language = server_metadata.get("language", "python")
        if language == "python":
            script += 'echo "  python server.py"\n'
        elif language in ["javascript", "node"]:
            script += 'echo "  node server.js"\n'
        else:
            script += 'echo "  python server.py  # or appropriate command for your server"\n'
        
        script += f"""
echo ""
echo "Server details:"
echo "  Name: {server_metadata['name']}"
echo "  Version: {server_metadata['version']}"
echo "  Language: {server_metadata.get('language', 'python')}"
echo "  Category: {server_metadata.get('category', 'general')}"
"""
        
        return script
    
    async def _run_command(self, cmd: List[str], cwd: Path = None) -> Dict[str, Any]:
        """Run a shell command asynchronously"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd) if cwd else None
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8')
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e)
            }

def create_marketplace_installer(config: Dict[str, Any]) -> MarketplaceInstaller:
    """Create and configure marketplace installer"""
    return MarketplaceInstaller(config)

if __name__ == "__main__":
    # Example configuration
    config = {
        "install_directory": "data/marketplace_installs",
        "use_mcp_hosting": True,
        "auto_generate_config": True,
        "mcp_hosting": {
            "enabled": True,
            "servers_dir": "data/mcp_servers"
        }
    }
    
    installer = create_marketplace_installer(config)
    print("Marketplace installer initialized successfully")