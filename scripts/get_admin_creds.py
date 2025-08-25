#!/usr/bin/env python3
"""
Get admin credentials from hAIveMind database
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from database import ControlDatabase

def main():
    db = ControlDatabase()
    # Database will show admin credentials during initialization if needed
    print("\nTo access the dashboard:")
    print("🌐 URL: http://localhost:8900/admin/dashboard.html")
    print("👤 Default username: admin")
    print("🔑 Check server startup logs for password")
    
    # Try to see if we can extract any user info
    try:
        with db.get_connection() as conn:
            cursor = conn.execute("SELECT username, email, role FROM users WHERE role = 'admin'")
            users = cursor.fetchall()
            
            print(f"\n📊 Found {len(users)} admin user(s):")
            for user in users:
                print(f"   • {user['username']} ({user['email']}) - {user['role']}")
                
    except Exception as e:
        print(f"Error reading users: {e}")

if __name__ == "__main__":
    main()