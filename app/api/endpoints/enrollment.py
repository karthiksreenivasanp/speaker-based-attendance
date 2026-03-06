from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from typing import List
import shutil
import os
import numpy as np
import pickle
from datetime import datetime

from app.db.database import get_db
from app import models, schemas
from app.core.config import settings
from app.ml_engine.processing import audio_processor
from app.ml_engine.embedding import speaker_model

router = APIRouter()

@router.post("/{student_id}")
async def enroll_student(
    student_id: int,
    name: str = Form(None),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    existing_roll = db.query(models.Student).filter(models.Student.roll_number == f"R-{student_id}").first()
    
    if not student:
        if name:
            if existing_roll:
                raise HTTPException(status_code=400, detail=f"Roll number R-{student_id} is already taken by another ID.")
            # Create new student on the fly
            student = models.Student(id=student_id, name=name, roll_number=f"R-{student_id}", course="Auto-Enrolled")
            db.add(student)
            db.commit()
            db.refresh(student)
        else:
            raise HTTPException(status_code=404, detail="Student ID not found. Provide a Name to create a new student.")
            
    if student and name:
         # Update name if provided
         student.name = name
         db.commit()

    if len(files) < 3:
        raise HTTPException(status_code=400, detail="Minimum 3 audio samples required")
    
    # Check total size to prevent huge uploads stalling
    total_size = sum([f.size for f in files if f.size])
    if total_size > 10 * 1024 * 1024: # 10MB limit
         raise HTTPException(status_code=400, detail="Total file size too large (max 10MB)")

    embeddings = []
    
    # Process each file
    try:
        for file in files:
            file_location = os.path.join(settings.UPLOAD_DIR, f"{student_id}_{file.filename}")
            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Load and process (disable noise reduction for speed in enrollment if needed, 
            # but usually it's better to keep it. We'll keep it but optimize imports)
            signal = audio_processor.load_audio(file_location, reduce_noise=True)
            signal = audio_processor.normalize_volume(signal)
            
            # Check duration - prevent processing huge files
            duration = signal.shape[1] / 16000
            if duration > 15: # Max 15 seconds per sample
                 os.remove(file_location)
                 raise HTTPException(status_code=400, detail=f"Sample {file.filename} is too long ({duration:.1f}s). Max 15s.")

            # Check quality (e.g., silence)
            if audio_processor.is_silent(signal):
                 os.remove(file_location)
                 raise HTTPException(status_code=400, detail=f"File {file.filename} is too silent.")

            # Extract embedding
            emb = speaker_model.get_embedding(signal)
            embeddings.append(emb)
            
            # Cleanup
            os.remove(file_location)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing Error: {str(e)}")

    # Average embeddings
    avg_embedding = np.mean(embeddings, axis=0)
    
    # Store in DB
    # Check if template exists, update or create
    existing_template = db.query(models.VoiceTemplate).filter(models.VoiceTemplate.student_id == student_id).first()
    if existing_template:
        existing_template.embedding = avg_embedding
        existing_template.enrollment_date = datetime.utcnow()
    else:
        new_template = models.VoiceTemplate(
            student_id=student_id,
            embedding=avg_embedding
        )
        db.add(new_template)
    
    db.commit()
    
    return {"message": "Enrollment successful", "samples_processed": len(files)}
