import os
import requests
import zipfile
import shutil
import glob

API_URL = "http://127.0.0.1:8000/api/v1"

def batch_enroll():
    print("=== 🎙️ Batch Voice Enrollment Tool ===")
    
    # 1. Get Student ID
    try:
        student_id = int(input("Enter Student ID to enroll: "))
        
        # Verify Name
        chk = requests.get(f"{API_URL}/students/{student_id}")
        if chk.status_code == 200:
            print(f"✅ Found Student: {chk.json()['name']}")
        else:
            print(f"⚠️  New Student ID (Name will be asked later)")
            
    except ValueError:
        print("❌ Invalid ID. Please enter a number.")
        return

    # 2. Get Dataset Path
    path = input("Enter path to your ZIP file or Folder (e.g., C:/data/voices.zip): ").strip().strip('"')
    
    if not os.path.exists(path):
        print("❌ File not found!")
        return

    # 3. Prepare Files
    temp_dir = "temp_dataset"
    if os.path.exists(temp_dir):
        import time
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
             time.sleep(1)
             shutil.rmtree(temp_dir, ignore_errors=True)
             
    if not os.path.exists(temp_dir):
         os.makedirs(temp_dir)

    audio_files = []
    
    try:
        if path.endswith(".zip"):
            print("📦 Extracting ZIP file...")
            with zipfile.ZipFile(path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find all wav files recursively
            audio_files = glob.glob(os.path.join(temp_dir, "**", "*.wav"), recursive=True)
            audio_files += glob.glob(os.path.join(temp_dir, "**", "*.mp3"), recursive=True)
        else:
            # It's a folder
            audio_files = glob.glob(os.path.join(path, "**", "*.wav"), recursive=True)
            audio_files += glob.glob(os.path.join(path, "**", "*.mp3"), recursive=True)

        if not audio_files:
            print("❌ No .wav or .mp3 files found in that location.")
            return

        print(f"✅ Found {len(audio_files)} audio samples.")
        
        # 4. Upload in Batch
        # We need to open all files simultaneously
        print("🚀 Uploading to server... (This involves AI processing, please wait)")
        
        files_to_send = []
        open_handles = []
        
        for i, fpath in enumerate(audio_files):
            fname = os.path.basename(fpath)
            fh = open(fpath, "rb")
            open_handles.append(fh)
            files_to_send.append(
                ('files', (fname, fh, "audio/wav")) # MIME type guessed
            )

        response = requests.post(f"{API_URL}/enroll/{student_id}", files=files_to_send)
        
        # Close handles
        for fh in open_handles:
            fh.close()

        if response.status_code == 200:
            print("\n🎉 SUCCESS! Batch Enrollment Complete.")
            print(response.json())
        elif response.status_code == 404 and "Student not found" in response.text:
            print(f"\n⚠️  Student ID {student_id} does not exist (database was reset?).")
            create_new = input(f"👉 Do you want to Register 'Student {student_id}' now? (y/n): ").strip().lower()
            
            if create_new == 'y':
                name_input = input(f"Enter Name for Student {student_id} (or press Enter for 'Student {student_id}'): ").strip()
                if not name_input: name_input = f"Student {student_id}"
                
                # Create Student
                reg_payload = {"name": name_input, "roll_number": str(student_id), "course": "Batch"}
                reg_resp = requests.post(f"{API_URL}/students/", json=reg_payload)
                
                if reg_resp.status_code == 200:
                    print(f"✅ Registered '{name_input}' (ID: {reg_resp.json()['id']}). Retrying enrollment...")
                    
                    # Retry Enrollment
                    # Re-open files since they were closed (or seek 0) - simpler to re-open loop logic
                    # Since we consumed the handles, we need to re-open.
                    # Let's verify we didn't close them yet... we close them in line 80.
                    # Wait, we need to close them then re-open.
                    for fh in open_handles: fh.close()
                    open_handles = []
                    files_to_send = []
                    
                    for i, fpath in enumerate(audio_files):
                        fname = os.path.basename(fpath)
                        fh = open(fpath, "rb")
                        open_handles.append(fh)
                        files_to_send.append(('files', (fname, fh, "audio/wav")))
                        
                    retry_resp = requests.post(f"{API_URL}/enroll/{student_id}", files=files_to_send)
                    
                    if retry_resp.status_code == 200:
                        print("\n🎉 SUCCESS! Batch Enrollment Complete.")
                        print(retry_resp.json())
                    else:
                        print(f"❌ Retry Failed: {retry_resp.text}")
                else:
                    print(f"❌ Registration Failed: {reg_resp.text}")
            else:
                print("❌ Skipped.")
        else:
            print("\n❌ FAILED.")
            print(f"Status: {response.status_code}")
            print(f"Detail: {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Cleanup with retry and error handling
        import time
        for fh in open_handles: # Ensure doublesure they are closed
             try: fh.close() 
             except: pass
             
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                time.sleep(1) # Wait a sec for Windows to release lock
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    print(f"⚠️ Warning: Could not delete temp folder {temp_dir}. You can delete it manually.")

if __name__ == "__main__":
    batch_enroll()
    input("\nPress Enter to exit...")
