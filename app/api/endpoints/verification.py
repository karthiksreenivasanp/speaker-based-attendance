from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from typing import Optional
import shutil
import os
import numpy as np
from datetime import datetime, timedelta
import math

from app.db.database import get_db
from app import models, schemas
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

def get_attendance_status(session_start: datetime, now: datetime) -> str:
    if not session_start:
        return "PRESENT" # Fallback if no start time set
    
    diff = (now - session_start).total_seconds() / 60.0
    
    if diff > 10.0:
        return "ABSENT" # Marked absent if late > 10 mins
    else:
        return "PRESENT"

@router.post("/", response_model=schemas.VerificationResponse)
async def verify_student(
    class_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    current_user: models.User = Depends(student_required),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    # 1. Fetch Student Template
    template = db.query(models.VoiceTemplate).filter(models.VoiceTemplate.student_id == student.id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Student not enrolled")

    # Fetch Class info
    if class_id:
        class_session = db.query(models.ClassSession).filter(models.ClassSession.id == class_id).first()
    else:
        if not student.mentor_id:
            raise HTTPException(status_code=400, detail="No mentor selected. Please select a teacher.")
        class_session = db.query(models.ClassSession).filter(
            models.ClassSession.teacher_id == student.mentor_id
        ).order_by(models.ClassSession.session_start.desc()).first()

    if not class_session:
        raise HTTPException(status_code=404, detail="No active class session found")
    
    # Auto-assign the class id for logging
    target_class_id = class_session.id

    # Requirement: Speaking only available if location is detected
    if latitude is None or longitude is None:
        raise HTTPException(status_code=400, detail="Location detection mandatory for attendance")

    # Strict Geofencing Check
    if class_session.latitude and class_session.longitude:
        distance = haversine(latitude, longitude, class_session.latitude, class_session.longitude)
        if distance > (class_session.radius or 20.0):
            raise HTTPException(
                status_code=403, 
                detail=f"Verification Failed: Outside allowed area ({distance:.1f}m away)"
            )

    # 2. Save and Process Audio
    file_location = os.path.join(settings.UPLOAD_DIR, f"verify_{student.id}_{datetime.utcnow().timestamp()}.wav")
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
        score = speaker_model.compute_similarity(emb, template.embedding)
        liveness_score = audio_processor.check_liveness(signal)
        
        is_match = score > VERIFICATION_THRESHOLD and liveness_score >= 0.5
        
        if not is_match:
             message = "Verification Failed: Spoofing detected" if liveness_score < 0.5 else "Verification Failed: Voice mismatch"
             return {
                 "verified": False,
                 "score": float(score),
                 "liveness_score": float(liveness_score),
                 "student_id": student.id,
                 "message": message,
                 "location_verified": True
             }

        # 5. Determine Status based on Timing
        now = datetime.utcnow()
        status = get_attendance_status(class_session.session_start, now)
        
        if status == "ABSENT":
            return {
                "verified": False,
                "score": float(score),
                "liveness_score": float(liveness_score),
                "student_id": student.id,
                "message": "Verification Failed: Session expired (over 45 mins)",
                "location_verified": True
            }

        # 6. Log Attendance
        attendance = models.Attendance(
            student_id=student.id,
            class_id=target_class_id,
            timestamp=now,
            status=status,
            verification_score=float(score),
            liveness_score=float(liveness_score),
            latitude=latitude,
            longitude=longitude
        )
        db.add(attendance)
        db.commit()
        
        return {
            "verified": True,
            "score": float(score),
            "liveness_score": float(liveness_score),
            "student_id": student.id,
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
    current_user: models.User = Depends(student_required),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student or not student.mentor_id:
        raise HTTPException(status_code=400, detail="Student must select a mentor first")

    # Requirement: speaking option only available if location detected
    if latitude is None or longitude is None:
        raise HTTPException(status_code=400, detail="Location detection mandatory for identification")

    # Find the latest "active" class session for the student's mentor
    class_session = db.query(models.ClassSession).filter(
        models.ClassSession.teacher_id == student.mentor_id
    ).order_by(models.ClassSession.session_start.desc()).first()

    if not class_session or not class_session.session_start:
        raise HTTPException(status_code=400, detail="No active class session found for your mentor")

    # Strict Geofencing Check
    if class_session.latitude and class_session.longitude:
        distance = haversine(latitude, longitude, class_session.latitude, class_session.longitude)
        if distance > (class_session.radius or 20.0):
             raise HTTPException(status_code=403, detail=f"Outside allowed area ({distance:.1f}m away)")

    # Save Upload
    file_location = os.path.join(settings.UPLOAD_DIR, f"identify_{datetime.utcnow().timestamp()}.wav")
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
        template = db.query(models.VoiceTemplate).filter(models.VoiceTemplate.student_id == student.id).first()
        if not template:
            return {"identified": False, "message": "Voice not enrolled"}
            
        score = speaker_model.compute_similarity(emb, template.embedding)
        
        is_identified = (score > VERIFICATION_THRESHOLD) and (liveness_score >= 0.5)
        
        if is_identified:
            now = datetime.utcnow()
            status = get_attendance_status(class_session.session_start, now)
            
            if status == "ABSENT":
                 return {"identified": False, "message": "Session expired (over 45 mins)"}

            # LOG ATTENDANCE
            attendance = models.Attendance(
                student_id=student.id,
                class_id=class_session.id,
                timestamp=now,
                status=status,
                verification_score=float(score),
                liveness_score=float(liveness_score),
                latitude=latitude,
                longitude=longitude
            )
            db.add(attendance)
            db.commit()
            
            return {
                "identified": True,
                "student_id": student.id,
                "name": student.name,
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
