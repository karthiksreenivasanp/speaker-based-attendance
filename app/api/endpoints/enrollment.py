from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from typing import List
import shutil
import os
import numpy as np
from datetime import datetime

from app.db.database import get_db
from app import schemas
from app.core.config import settings
from app.ml_engine.processing import audio_processor
from app.ml_engine.embedding import speaker_model

router = APIRouter()

@router.post("/{student_id}")
async def enroll_student(
    student_id: str,
    name: str = Form(None),
    files: List[UploadFile] = File(...),
    db = Depends(get_db)
):
    student_ref = db.collection("students").document(student_id)
    student_doc = student_ref.get()
    
    if not student_doc.exists:
        if name:
            existing_rolls = db.collection("students").where("roll_number", "==", f"R-{student_id}").limit(1).get()
            if existing_rolls:
                raise HTTPException(status_code=400, detail=f"Roll number R-{student_id} is already taken.")
            
            student_ref.set({
                "user_id": student_id,
                "name": name,
                "roll_number": f"R-{student_id}",
                "course": "Auto-Enrolled",
                "mentor_id": None
            })
        else:
            raise HTTPException(status_code=404, detail="Student ID not found. Provide a Name to create a new student.")
    else:
        if name:
             student_ref.update({"name": name})

    if len(files) < 3:
        raise HTTPException(status_code=400, detail="Minimum 3 audio samples required")
    
    total_size = sum([f.size for f in files if f.size])
    if total_size > 10 * 1024 * 1024:
         raise HTTPException(status_code=400, detail="Total file size too large (max 10MB)")

    embeddings = []
    
    try:
        for file in files:
            file_location = os.path.join(settings.UPLOAD_DIR, f"{student_id}_{file.filename}")
            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            signal = audio_processor.load_audio(file_location, reduce_noise=True)
            signal = audio_processor.normalize_volume(signal)
            
            duration = signal.shape[1] / 16000
            if duration > 15:
                 os.remove(file_location)
                 raise HTTPException(status_code=400, detail=f"Sample {file.filename} is too long ({duration:.1f}s). Max 15s.")

            if audio_processor.is_silent(signal):
                 os.remove(file_location)
                 raise HTTPException(status_code=400, detail=f"File {file.filename} is too silent.")

            emb = speaker_model.get_embedding(signal)
            embeddings.append(emb)
            os.remove(file_location)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Speaker model unavailable: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing Error: {str(e)}")

    avg_embedding = np.mean(embeddings, axis=0)
    
    template_docs = db.collection("voice_templates").where("student_id", "==", student_id).limit(1).get()
    
    if template_docs:
        template_docs[0].reference.update({
            "embedding": avg_embedding.tolist(),
            "enrollment_date": datetime.utcnow()
        })
    else:
        db.collection("voice_templates").add({
            "student_id": student_id,
            "embedding": avg_embedding.tolist(),
            "enrollment_date": datetime.utcnow()
        })
    
    return {"message": "Enrollment successful", "samples_processed": len(files)}
