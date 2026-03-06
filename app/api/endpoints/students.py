from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app import models, schemas
from app.api.deps import get_current_active_user, student_required

router = APIRouter()

@router.get("/me", response_model=schemas.User)
def read_user_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

@router.get("/profile", response_model=schemas.Student)
def read_student_profile(
    current_user: models.User = Depends(student_required),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return student

@router.get("/mentors", response_model=List[schemas.User])
def read_available_mentors(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return db.query(models.User).filter(models.User.role == models.UserRole.TEACHER).all()

@router.post("/select-mentor/{teacher_id}")
def select_mentor(
    teacher_id: int,
    current_user: models.User = Depends(student_required),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    if student.mentor_id is not None:
        raise HTTPException(
            status_code=400, 
            detail="Mentor already selected. Contact your mentor to change it."
        )
    
    teacher = db.query(models.User).filter(
        models.User.id == teacher_id, 
        models.User.role == models.UserRole.TEACHER
    ).first()
    
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    student.mentor_id = teacher.id
    db.commit()
    return {"message": "Mentor selected successfully", "mentor_name": teacher.username}

@router.get("/voice")
def get_voice_status(
    current_user: models.User = Depends(student_required),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
        
    template = db.query(models.VoiceTemplate).filter(models.VoiceTemplate.student_id == student.id).first()
    if not template:
        return {"enrolled": False}
        
    return {
        "enrolled": True,
        "enrollment_date": template.enrollment_date
    }

@router.delete("/voice")
def delete_voice_template(
    current_user: models.User = Depends(student_required),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
        
    template = db.query(models.VoiceTemplate).filter(models.VoiceTemplate.student_id == student.id).first()
    if not template:
        raise HTTPException(status_code=404, detail="No voice template found")
        
    db.delete(template)
    db.commit()
    return {"message": "Voice template deleted successfully"}

# Other endpoints can be protected as needed
@router.get("/", response_model=List[schemas.Student])
def read_students(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Teachers can see all students, students can see themselves? 
    # For now keep it open but protected by login
    students = db.query(models.Student).offset(skip).limit(limit).all()
    return students
