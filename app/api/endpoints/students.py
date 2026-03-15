from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.db.database import get_db
from app import schemas
from app.api.deps import get_current_active_user, student_required

router = APIRouter()

@router.get("/me", response_model=schemas.User)
def read_user_me(current_user: schemas.User = Depends(get_current_active_user)):
    return current_user

@router.get("/profile", response_model=schemas.Student)
def read_student_profile(
    current_user: schemas.User = Depends(student_required),
    db = Depends(get_db)
):
    student_doc = db.collection("students").document(current_user.id).get()
    if not student_doc.exists:
        raise HTTPException(status_code=404, detail="Student profile not found")
    student_data = student_doc.to_dict()
    return schemas.Student(**student_data, id=student_doc.id)

@router.get("/mentors", response_model=List[schemas.User])
def read_available_mentors(
    current_user: schemas.User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    mentors = db.collection("users").where("role", "==", schemas.UserRole.TEACHER.value).get()
    return [schemas.User(**m.to_dict(), id=m.id) for m in mentors]

@router.post("/select-mentor/{teacher_id}")
def select_mentor(
    teacher_id: str,
    current_user: schemas.User = Depends(student_required),
    db = Depends(get_db)
):
    student_ref = db.collection("students").document(current_user.id)
    student_doc = student_ref.get()
    if not student_doc.exists:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    student_data = student_doc.to_dict()
    if student_data.get("mentor_id"):
        raise HTTPException(
            status_code=400, 
            detail="Mentor already selected. Contact your mentor to change it."
        )
    
    teacher_doc = db.collection("users").document(teacher_id).get()
    if not teacher_doc.exists or teacher_doc.to_dict().get("role") != schemas.UserRole.TEACHER.value:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    student_ref.update({"mentor_id": teacher_id})
    return {"message": "Mentor selected successfully", "mentor_name": teacher_doc.to_dict().get("username")}

@router.get("/voice")
def get_voice_status(
    current_user: schemas.User = Depends(student_required),
    db = Depends(get_db)
):
    template_docs = db.collection("voice_templates").where("student_id", "==", current_user.id).limit(1).get()
    if not template_docs:
        return {"enrolled": False}
        
    template_data = template_docs[0].to_dict()
    return {
        "enrolled": True,
        "enrollment_date": template_data.get("enrollment_date")
    }

@router.delete("/voice")
def delete_voice_template(
    current_user: schemas.User = Depends(student_required),
    db = Depends(get_db)
):
    template_docs = db.collection("voice_templates").where("student_id", "==", current_user.id).limit(1).get()
    if not template_docs:
        raise HTTPException(status_code=404, detail="No voice template found")
        
    template_docs[0].reference.delete()
    return {"message": "Voice template deleted successfully"}

# Other endpoints can be protected as needed
@router.get("/", response_model=List[schemas.Student])
def read_students(
    skip: int = 0, 
    limit: int = 100, 
    db = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    docs = db.collection("students").limit(limit).get()
    return [schemas.Student(**d.to_dict(), id=d.id) for d in docs]
