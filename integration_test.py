import requests
import numpy as np
import scipy.io.wavfile as wav
import os
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"
GENERATED_FILES = []

def generate_wav(filename, frequency=440, duration=3.0, sample_rate=16000):
    """Generates a dummy sine wave audio file."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Generate a complex signal to have some features
    audio_data = 0.5 * np.sin(2 * np.pi * frequency * t) + \
                 0.3 * np.sin(2 * np.pi * (frequency * 1.5) * t) + \
                 0.2 * np.sin(2 * np.pi * (frequency * 0.5) * t)
    
    # Add some noise to make it realistic enough (not pure silence)
    noise = np.random.normal(0, 0.01, audio_data.shape)
    final_audio = audio_data + noise
    
    # Normalize to 16-bit range
    final_audio = np.int16(final_audio / np.max(np.abs(final_audio)) * 32767)
    
    wav.write(filename, sample_rate, final_audio)
    GENERATED_FILES.append(filename)
    return filename

def test_workflow():
    print("1. Creating Student...")
    student_data = {
        "name": "Test Student",
        "roll_number": f"TEST_{int(time.time())}",
        "course": "Computer Science"
    }
    resp = requests.post(f"{BASE_URL}/students/", json=student_data)
    if resp.status_code != 200:
        print("FAILED:", resp.text)
        return
    student = resp.json()
    student_id = student["id"]
    print(f"Student Created: ID={student_id}")

    print("\n2. Enrolling Student (3 samples)...")
    # Generate 3 similar samples (simulate same voice)
    f1 = generate_wav("sample1.wav", 400)
    f2 = generate_wav("sample2.wav", 405) # Slight variation
    f3 = generate_wav("sample3.wav", 395) # Slight variation
    
    files = [
        ('files', open(f1, 'rb')),
        ('files', open(f2, 'rb')),
        ('files', open(f3, 'rb'))
    ]
    resp = requests.post(f"{BASE_URL}/enroll/{student_id}", files=files)
    for _, f in files: f.close()
    
    if resp.status_code == 200:
        print("Enrollment Successful")
    else:
        print("Enrollment FAILED:", resp.text)
        return

    print("\n3. Verifying (Correct Voice)...")
    f_verify = generate_wav("verify_correct.wav", 402) # Very close
    verify_files = {'file': open(f_verify, 'rb')}
    data = {'student_id': student_id, 'class_id': 101}
    
    resp = requests.post(f"{BASE_URL}/verify/", files=verify_files, data=data)
    verify_files['file'].close()
    
    result = resp.json()
    print("Verification Result:", result)
    if result.get("verified"):
        print("PASS: Correctly Verified")
    else:
        print("FAIL: Should have verified")

    print("\n4. Verifying (Imposter Voice)...")
    f_imposter = generate_wav("imposter.wav", 800) # Totally different freq
    verify_files = {'file': open(f_imposter, 'rb')}
    
    resp = requests.post(f"{BASE_URL}/verify/", files=verify_files, data=data)
    verify_files['file'].close()
    
    result = resp.json()
    print("Verification Result:", result)
    if not result.get("verified"):
        print("PASS: Correctly Rejected")
    else:
        print("FAIL: Should have rejected")

    # Cleanup
    for f in GENERATED_FILES:
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    try:
        test_workflow()
    except Exception as e:
        print("Test Error (Is the server running?):", e)
