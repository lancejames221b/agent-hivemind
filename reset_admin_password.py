#!/usr/bin/env python3
"""
Reset admin password for hAIveMind dashboard
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from database import ControlDatabase
import bcrypt

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 reset_admin_password.py <new_password>")
        print("Example: python3 reset_admin_password.py admin123!")
        return
    
    password = sys.argv[1]
    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return
    
    # Update database
    db = ControlDatabase()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    with db.get_connection() as conn:
        cursor = conn.execute("""
            UPDATE users SET password_hash = ? WHERE username = 'admin'
        """, (password_hash,))
        
        if cursor.rowcount > 0:
            print("✅ Admin password updated successfully!")
            print("\n🌐 Dashboard Access:")
            print("   URL: http://localhost:8901/admin/dashboard.html")
            print("   Username: admin")
            print("   Password: [your new password]")
        else:
            print("❌ Failed to update admin password")

if __name__ == "__main__":
    main()