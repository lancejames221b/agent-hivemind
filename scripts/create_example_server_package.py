#!/usr/bin/env python3
"""
Script to create an example MCP server package for testing hAIveMind hosting
"""

import base64
import json
import zipfile
from pathlib import Path
import tempfile
import shutil

def create_example_server_package():
    """Create a ZIP package of the example MCP server"""
    
    # Get the examples directory
    examples_dir = Path(__file__).parent.parent / "examples" / "mcp_server_examples"
    
    if not examples_dir.exists():
        print(f"❌ Examples directory not found: {examples_dir}")
        return None
    
    # Create temporary directory for packaging
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        package_dir = temp_path / "simple_mcp_server"
        package_dir.mkdir()
        
        # Copy files to package directory
        files_to_copy = [
            "simple_python_server.py",
            "requirements.txt",
            "server_config.json"
        ]
        
        for file_name in files_to_copy:
            src_file = examples_dir / file_name
            if src_file.exists():
                shutil.copy2(src_file, package_dir / file_name)
                print(f"✅ Copied {file_name}")
            else:
                print(f"⚠️ File not found: {file_name}")
        
        # Create ZIP archive
        zip_path = temp_path / "simple_mcp_server.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in package_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)
                    print(f"📦 Added to ZIP: {arcname}")
        
        # Read ZIP file and encode as base64
        with open(zip_path, 'rb') as f:
            zip_data = f.read()
        
        base64_data = base64.b64encode(zip_data).decode('utf-8')
        
        # Create upload command
        upload_command = {
            "tool": "upload_mcp_server",
            "parameters": {
                "name": "Simple Python MCP Server",
                "description": "A basic example Python MCP server for demonstration purposes",
                "archive_base64": base64_data,
                "command": ["python", "simple_python_server.py"],
                "environment": {
                    "PYTHONPATH": ".",
                    "MCP_SERVER_NAME": "simple-example"
                },
                "auto_restart": True,
                "resource_limits": {
                    "memory_mb": 256,
                    "cpu_percent": 30
                },
                "user_id": "example_creator"
            }
        }
        
        # Save the command to a file for easy use
        output_dir = Path(__file__).parent.parent / "examples"
        command_file = output_dir / "upload_example_server.json"
        
        with open(command_file, 'w') as f:
            json.dump(upload_command, f, indent=2)
        
        print(f"\n✅ Example server package created!")
        print(f"📄 Upload command saved to: {command_file}")
        print(f"📦 Package size: {len(zip_data)} bytes")
        print(f"🔢 Base64 size: {len(base64_data)} characters")
        
        return {
            "zip_size": len(zip_data),
            "base64_size": len(base64_data),
            "command_file": str(command_file),
            "upload_command": upload_command
        }

if __name__ == "__main__":
    print("🏭 Creating example MCP server package for hAIveMind hosting...")
    result = create_example_server_package()
    
    if result:
        print(f"\n🎯 Ready to test! Use the upload command in {result['command_file']}")
        print("💡 You can also use this data directly with the upload_mcp_server tool")
    else:
        print("❌ Failed to create example package")