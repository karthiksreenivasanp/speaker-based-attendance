import requests

API_URL = "http://127.0.0.1:8000/api/v1"

def register_students():
    print("=== 📝 Student Registration Tool ===")
    print("Enter 'q' to quit at any time.\n")
    
    while True:
        try:
            val = input("Enter Student ID to Register (e.g. 1): ").strip()
            if val.lower() == 'q': break
            
            student_id = int(val)
            name = input(f"Enter Name for ID {student_id}: ").strip()
            if not name: name = f"Student {student_id}"
            
            payload = {
                "name": name,
                "roll_number": str(student_id),
                "course": "Batch Enrolled"
            }
            
            resp = requests.post(f"{API_URL}/students/", json=payload)
            
            if resp.status_code == 200:
                print(f"✅ Success! Created Student ID: {resp.json()['id']}")
            elif resp.status_code == 400 and "already registered" in resp.text:
                print(f"ℹ️  Student ID {student_id} already exists. Skipping.")
            else:
                print(f"❌ Failed: {resp.text}")
                
        except ValueError:
            print("Please enter a valid number.")
        except Exception as e:
            print(f"Error: {e}")
            
    print("\nRegistration done. Now you can run batch_enroll.py!")

if __name__ == "__main__":
    register_students()
