#!/usr/bin/env python3
"""
Quick start script for hAIveMind services
"""
import subprocess
import time
import sys
import os
import requests

def check_service(url, name):
    """Check if a service is running"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {name} is running")
            return True
        else:
            print(f"❌ {name} returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {name} is not running")
        return False
    except Exception as e:
        print(f"❌ Error checking {name}: {e}")
        return False

def start_service(script_path, service_name, log_file):
    """Start a service in the background"""
    try:
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        # Start the service
        with open(f"logs/{log_file}", "w") as f:
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=os.getcwd()
            )
        
        print(f"🚀 Started {service_name} (PID: {process.pid})")
        return process.pid
    except Exception as e:
        print(f"❌ Failed to start {service_name}: {e}")
        return None

def main():
    """Main function to start hAIveMind services"""
    print("🧠 hAIveMind Quick Start")
    print("=" * 30)
    
    # Check if services are already running
    print("\n🔍 Checking service status...")
    
    remote_running = check_service("http://localhost:8900/health", "Remote MCP Server")
    sync_running = check_service("http://localhost:8899/api/status", "Sync Service")
    
    if remote_running and sync_running:
        print("\n🎉 All services are already running!")
        return
    
    print("\n🚀 Starting missing services...")
    
    # Start Remote MCP Server if not running
    if not remote_running:
        pid = start_service("src/remote_mcp_server.py", "Remote MCP Server", "remote_mcp_server.log")
        if pid:
            time.sleep(3)  # Give it time to start
    
    # Start Sync Service if not running  
    if not sync_running:
        pid = start_service("src/sync_service.py", "Sync Service", "sync_service.log")
        if pid:
            time.sleep(3)  # Give it time to start
    
    # Wait a bit more for services to fully initialize
    print("\n⏳ Waiting for services to initialize...")
    time.sleep(5)
    
    # Check services again
    print("\n🔍 Verifying services are running...")
    remote_ok = check_service("http://localhost:8900/health", "Remote MCP Server")
    sync_ok = check_service("http://localhost:8899/api/status", "Sync Service")
    
    if remote_ok and sync_ok:
        print("\n🎉 hAIveMind services started successfully!")
        print("\n📋 Service URLs:")
        print("  • Remote MCP Server: http://localhost:8900")
        print("  • Sync Service: http://localhost:8899")
        print("\n📊 Monitor logs:")
        print("  • tail -f logs/remote_mcp_server.log")
        print("  • tail -f logs/sync_service.log")
    else:
        print("\n❌ Some services failed to start properly.")
        print("Check the log files in the logs/ directory for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()