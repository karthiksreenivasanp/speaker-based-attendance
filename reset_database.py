import os
import time

DB_FILE = "voice_attendance.db"

def reset_db():
    print(f"🗑️  Attempting to delete {DB_FILE}...")
    
    if not os.path.exists(DB_FILE):
        print("✅ Database file does not exist. Already clean!")
        return

    try:
        os.remove(DB_FILE)
        print("✅ Database deleted successfully!")
        print("🔄 Please RESTART your server (uvicorn) to recreate empty tables.")
    except PermissionError:
        print("❌ Permission Denied!")
        print("⚠️  The server is likely still running and holding the file.")
        print("👉 Please STOP the server (Ctrl+C in the uvicorn window) and try running this script again.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    reset_db()
    input("\nPress Enter to exit...")
