from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from typing import Optional
import shutil
import os
import numpy as np
from datetime import datetime, timezone
import math
import uuid

from app.db.database import get_db
from app import schemas
from app.core.config import settings
from app.ml_engine.processing import audio_processor
from app.ml_engine.embedding import speaker_model
from app.api.deps import get_current_active_user, student_required

router = APIRouter()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

VERIFICATION_THRESHOLD = 0.20 

def get_attendance_status(session_start, now: datetime) -> str:
    if not session_start:
        return "PRESENT" # Fallback if no start time set
    
    # Handle ISO strings returning from Firestore instead of Objects
    if isinstance(session_start, str):
        try:
             # Fast API / Python 3.12 handles isoformat parsing natively. 
             # Ensure Z is replaced if it is there for explicit UTC
             session_start = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
        except ValueError:
             return "PRESENT" # Fallback on unparseable date
    
    # Ensure session_start is timezone-aware for comparison
    if session_start.tzinfo is None:
        session_start = session_start.replace(tzinfo=timezone.utc)
    
    diff = (now - session_start).total_seconds() / 60.0
    
    if diff > 10.0:
        return "ABSENT" # Marked absent if late > 10 mins
    else:
        return "PRESENT"

@router.post("/", response_model=schemas.VerificationResponse)
async def verify_student(
    class_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    current_user: schemas.User = Depends(student_required),
    db = Depends(get_db)
):
    student_doc = db.collection("students").document(current_user.id).get()
    if not student_doc.exists:
        raise HTTPException(status_code=404, detail="Student profile not found")
    student = student_doc.to_dict()

    # 1. Fetch Student Template
    templates = db.collection("voice_templates").where("student_id", "==", current_user.id).limit(1).get()
    if not templates:
        raise HTTPException(status_code=404, detail="Student not enrolled")
    
    template_data = templates[0].to_dict()
    template_embedding = np.array(template_data.get("embedding"))

    # Fetch Class info
    if class_id:
        class_doc = db.collection("classes").document(class_id).get()
        if not class_doc.exists:
             raise HTTPException(status_code=404, detail="No active class session found")
        class_session = class_doc.to_dict()
        class_session["id"] = class_doc.id # Add document ID to the dict
    else:
        mentor_id = student.get("mentor_id")
        if not mentor_id:
            raise HTTPException(status_code=400, detail="No mentor selected. Please select a teacher.")
        
        from google.cloud.firestore import Query as FSQuery
        classes = db.collection("classes").where("teacher_id", "==", mentor_id).order_by("session_start", direction=FSQuery.DESCENDING).limit(1).get()
        
        if not classes:
             raise HTTPException(status_code=404, detail="No active class session found")
        class_session = classes[0].to_dict()
        class_session["id"] = classes[0].id # Add document ID to the dict

    # Auto-assign the class id for logging
    target_class_id = class_session.get("id")

    # Requirement: Speaking only available if location is detected
    if latitude is None or longitude is None:
        raise HTTPException(status_code=400, detail="Location detection mandatory for attendance")

    # Strict Geofencing Check
    c_lat, c_lon = class_session.get("latitude"), class_session.get("longitude")
    if c_lat is not None and c_lon is not None:
        distance = haversine(latitude, longitude, c_lat, c_lon)
        if distance > class_session.get("radius", 20.0): # Default radius to 20.0 if not set
            raise HTTPException(
                status_code=403, 
                detail=f"Verification Failed: Outside allowed area ({distance:.1f}m away)"
            )

    # 2. Save and Process Audio
    file_location = os.path.join(settings.UPLOAD_DIR, f"verify_{current_user.id}_{datetime.now().timestamp()}.wav")
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        signal = audio_processor.load_audio(file_location)
        signal = audio_processor.normalize_volume(signal)
        
        if audio_processor.is_silent(signal):
             raise HTTPException(status_code=400, detail="Audio too silent")

        # 3. Extract Embedding
        emb = speaker_model.get_embedding(signal)
        
        # 4. Compare
        score = speaker_model.compute_similarity(emb, template_embedding)
        liveness_score = audio_processor.check_liveness(signal)
        
        is_match = score > VERIFICATION_THRESHOLD and liveness_score >= 0.5
        
        if not is_match:
             message = "Verification Failed: Spoofing detected" if liveness_score < 0.5 else "Verification Failed: Voice mismatch"
             return {
                 "verified": False,
                 "score": float(score),
                 "liveness_score": float(liveness_score),
                 "student_id": current_user.id,
                 "message": message,
                 "location_verified": True
             }

        # 5. Determine Status based on Timing
        now = datetime.now(timezone.utc)
        status = get_attendance_status(class_session.get("session_start"), now)
        
        if status == "ABSENT":
            return {
                "verified": False,
                "score": float(score),
                "liveness_score": float(liveness_score),
                "student_id": current_user.id,
                "message": "Verification Failed: Session expired (over 45 mins)",
                "location_verified": True
            }

        # 6. Log Attendance
        attendance_id = str(uuid.uuid4())
        attendance_data = {
            "student_id": current_user.id,
            "class_id": target_class_id,
            "timestamp": now.isoformat(),
            "status": status,
            "is_approved": False, # New field for Firestore
            "verification_score": float(score),
            "liveness_score": float(liveness_score),
            "latitude": latitude,
            "longitude": longitude
        }
        db.collection("attendance").document(attendance_id).set(attendance_data)
        
        return {
            "verified": True,
            "score": float(score),
            "liveness_score": float(liveness_score),
            "student_id": current_user.id,
            "message": f"Verified successfully as {status}",
            "location_verified": True
        }
        
    finally:
        if os.path.exists(file_location):
            os.remove(file_location)

@router.post("/identify")
async def identify_speaker(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    current_user: schemas.User = Depends(student_required),
    db = Depends(get_db)
):
    print(f"[IDENTIFY] Starting identification for user: '{current_user.id}'")
    student_doc = db.collection("students").document(current_user.id).get()
    if not student_doc.exists:
        raise HTTPException(status_code=400, detail="Student profile missing")
    student = student_doc.to_dict()
    student["id"] = student_doc.id # Add document ID to the dict
    print(f"[IDENTIFY] Student doc ID: '{student_doc.id}', mentor: '{student.get('mentor_id')}'")

    if not student.get("mentor_id"):
        raise HTTPException(status_code=400, detail="Student must select a mentor first")

    # Requirement: speaking option only available if location detected
    if latitude is None or longitude is None:
        raise HTTPException(status_code=400, detail="Location detection mandatory for identification")

    # Find the latest "active" class session for the student's mentor
    from google.cloud.firestore import Query as FSQuery
    try:
        classes = db.collection("classes").where("teacher_id", "==", student.get("mentor_id")).order_by("session_start", direction=FSQuery.DESCENDING).limit(1).get()
    except Exception as e:
        print(f"[IDENTIFY] Classes query failed (missing index?): {e}")
        # Fallback: fetch without order_by
        classes = db.collection("classes").where("teacher_id", "==", student.get("mentor_id")).limit(1).get()
    
    if not classes:
        raise HTTPException(status_code=400, detail="No active class session found for your mentor")
    
    class_session = classes[0].to_dict()
    class_session["id"] = classes[0].id # Add document ID to the dict
    print(f"[IDENTIFY] Found class session: '{class_session['id']}'")

    # Strict Geofencing Check
    c_lat, c_lon = class_session.get("latitude"), class_session.get("longitude")
    if c_lat is not None and c_lon is not None:
        distance = haversine(latitude, longitude, c_lat, c_lon)
        print(f"[IDENTIFY] Distance from class: {distance:.1f}m (radius: {class_session.get('radius', 20.0)}m)")
        if distance > class_session.get("radius", 20.0):
             raise HTTPException(status_code=403, detail=f"Outside allowed area ({distance:.1f}m away)")

    # Save Upload
    file_location = os.path.join(settings.UPLOAD_DIR, f"identify_{datetime.now().timestamp()}.wav")
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        signal = audio_processor.load_audio(file_location)
        signal = audio_processor.normalize_volume(signal)
        if audio_processor.is_silent(signal):
             return {"identified": False, "message": "Audio too silent"}

        liveness_score = audio_processor.check_liveness(signal)
        emb = speaker_model.get_embedding(signal)
        
        # Verify it matches the logged-in student
        print(f"[IDENTIFY] Looking for voice_templates with student_id='{current_user.id}'")
        templates = db.collection("voice_templates").where("student_id", "==", current_user.id).limit(1).get()
        
        # Debug: list all templates to see what's actually in the collection
        if not templates:
            all_templates = db.collection("voice_templates").limit(10).get()
            print(f"[IDENTIFY] No template found! All templates in DB:")
            for t in all_templates:
                t_data = t.to_dict()
                print(f"  - doc_id='{t.id}', student_id='{t_data.get('student_id')}'")
            return {"identified": False, "message": f"Voice not enrolled (looked for student_id='{current_user.id}')"}
            
        template_data = templates[0].to_dict()
        template_embedding = np.array(template_data.get("embedding"))
        score = speaker_model.compute_similarity(emb, template_embedding)
        
        is_identified = (score > VERIFICATION_THRESHOLD) and (liveness_score >= 0.5)
        
        if is_identified:
            now = datetime.now(timezone.utc)
            status = get_attendance_status(class_session.get("session_start"), now)
            
            if status == "ABSENT":
                 return {"identified": False, "message": "Session expired (over 45 mins)"}

            attendance_id = str(uuid.uuid4())
            attendance_data = {
                "student_id": current_user.id,
                "class_id": class_session.get("id"),
                "timestamp": now.isoformat(),
                "status": status,
                "is_approved": False, # New field for Firestore
                "verification_score": float(score),
                "liveness_score": float(liveness_score),
                "latitude": latitude,
                "longitude": longitude
            }
            db.collection("attendance").document(attendance_id).set(attendance_data)
            
            return {
                "identified": True,
                "student_id": current_user.id,
                "name": student.get("name"),
                "score": float(score),
                "liveness_score": float(liveness_score),
                "location_verified": True,
                "message": f"Identified as {status}"
            }
        else:
            return {
                "identified": False,
                "message": "Voice mismatch or Spoofing detected",
                "score": float(score),
                "liveness_score": float(liveness_score)
            }
            
    finally:
         if os.path.exists(file_location):
            os.remove(file_location)
