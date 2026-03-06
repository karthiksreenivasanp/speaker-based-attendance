from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io
from datetime import datetime

from app.db.database import get_db
from app import models, schemas
from app.api.deps import teacher_required, get_current_active_user

router = APIRouter()

@router.get("/classes/active", response_model=schemas.ClassSession)
def get_active_class(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(teacher_required)
):
    class_session = db.query(models.ClassSession).filter(
        models.ClassSession.teacher_id == current_user.id
    ).order_by(models.ClassSession.session_start.desc()).first()
    
    if not class_session:
        raise HTTPException(status_code=404, detail="No active class found")
    return class_session

@router.post("/classes/start", response_model=schemas.ClassSession)
def start_class_session(
    location: schemas.ClassLocationUpdate,
    course_id: str = Query("DEFAULT_COURSE"),
    room: str = Query("Main Hall"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(teacher_required)
):
    now = datetime.utcnow()
    new_session = models.ClassSession(
        course_id=course_id,
        teacher_id=current_user.id,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M"),
        session_start=now,
        room=room,
        latitude=location.latitude,
        longitude=location.longitude,
        radius=location.radius or 20.0
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@router.get("/attendance", response_model=List[schemas.Attendance])
def read_attendance(
    skip: int = 0, 
    limit: int = 100, 
    class_id: Optional[int] = None,
    student_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.Attendance)
    
    # If student, they can only see their own attendance
    if current_user.role == models.UserRole.STUDENT:
        student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found")
        query = query.filter(models.Attendance.student_id == student.id)
    else:
        # Teachers can see attendance of their mentored students
        if class_id:
            query = query.filter(models.Attendance.class_id == class_id)
        if student_id:
            query = query.filter(models.Attendance.student_id == student_id)
            
    return query.offset(skip).limit(limit).all()

@router.patch("/attendance/{attendance_id}")
def update_attendance_status(
    attendance_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(teacher_required)
):
    attendance = db.query(models.Attendance).filter(models.Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Check if this teacher is the mentor
    if attendance.student.mentor_id != current_user.id:
         raise HTTPException(status_code=403, detail="You can only change attendance for your mentored students")
         
    attendance.status = status
    db.commit()
    return {"message": "Attendance status updated", "new_status": status}

@router.post("/attendance/approve")
def approve_attendance(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(teacher_required)
):
    # Approve all unapproved records for the teacher's mentored students
    students = db.query(models.Student).filter(models.Student.mentor_id == current_user.id).all()
    student_ids = [s.id for s in students]
    
    db.query(models.Attendance).filter(
        models.Attendance.student_id.in_(student_ids),
        models.Attendance.is_approved == False
    ).update({"is_approved": True}, synchronize_session=False)
    
    db.commit()
    return {"message": "Attendance sheet approved"}

@router.get("/attendance/export")
def export_attendance_csv(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(teacher_required)
):
    # Export all approved records for the teacher's students
    attendance_query = db.query(models.Attendance)\
        .join(models.Student, models.Attendance.student_id == models.Student.id)\
        .filter(models.Attendance.is_approved == True)\
        .filter(models.Student.mentor_id == current_user.id)
    
    attendance_records = attendance_query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Name", "Roll Number", "Course", "Status", "Time", "Confidence Score", "Approved"])
    
    for record in attendance_records:
        writer.writerow([
            record.student.id,
            record.student.name,
            record.student.roll_number,
            record.student.course,
            record.status,
            record.timestamp,
            f"{record.verification_score:.2f}",
            record.is_approved
        ])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()), 
        media_type="text/csv", 
        headers={"Content-Disposition": f"attachment; filename=approved_attendance_{datetime.now().strftime('%Y%m%d')}.csv"}
    )
