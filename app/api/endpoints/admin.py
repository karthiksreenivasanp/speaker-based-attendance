from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, Optional
import csv
import io
from datetime import datetime, timezone
import uuid

from app.db.database import get_db
from app import schemas
from app.api.deps import teacher_required, get_current_active_user

router = APIRouter()

@router.get("/classes/active", response_model=schemas.ClassSession)
def get_active_class(
    db = Depends(get_db),
    current_user: schemas.User = Depends(teacher_required)
):
    from google.cloud.firestore import Query as FSQuery
    sessions = db.collection("classes").where("teacher_id", "==", current_user.id).order_by("session_start", direction=FSQuery.DESCENDING).limit(1).get()
    
    if not sessions:
        raise HTTPException(status_code=404, detail="No active class found")
    
    session_data = sessions[0].to_dict()
    return schemas.ClassSession(**session_data, id=sessions[0].id)

@router.post("/classes/start", response_model=schemas.ClassSession)
def start_class_session(
    location: schemas.ClassLocationUpdate,
    course_id: str = Query("DEFAULT_COURSE"),
    room: str = Query("Main Hall"),
    db = Depends(get_db),
    current_user: schemas.User = Depends(teacher_required)
):
    now = datetime.now(timezone.utc)
    new_id = str(uuid.uuid4())
    class_data = {
        "course_id": course_id,
        "teacher_id": current_user.id,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "session_start": now, # Firestore automatically converts to proper Timestamp
        "room": room,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "radius": location.radius or 20.0
    }
    
    db.collection("classes").document(new_id).set(class_data)
    
    return schemas.ClassSession(**class_data, id=new_id)

@router.get("/attendance", response_model=List[schemas.Attendance])
def read_attendance(
    skip: int = 0, 
    limit: int = 100, 
    class_id: Optional[str] = None,
    student_id: Optional[str] = None,
    db = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    from google.cloud.firestore import Query as FSQuery
    query = db.collection("attendance")
    
    if current_user.role == schemas.UserRole.STUDENT:
        student_doc = db.collection("students").document(current_user.id).get()
        if not student_doc.exists:
            raise HTTPException(status_code=404, detail="Student profile not found")
        query = query.where("student_id", "==", current_user.id)
    else:
        if class_id:
            query = query.where("class_id", "==", class_id)
        if student_id:
            query = query.where("student_id", "==", student_id)
            
    try:
        docs = query.order_by("timestamp", direction=FSQuery.DESCENDING).limit(limit).get()
        return [schemas.Attendance(**d.to_dict(), id=d.id) for d in docs]
    except Exception as e:
        print(f"Firestore Query Error (likely missing index): {e}")
        # If the index is missing, return empty or un-ordered list to not break the frontend
        try:
            docs = query.limit(limit).get()
            return [schemas.Attendance(**d.to_dict(), id=d.id) for d in docs]
        except Exception as e2:
            print(f"Fallback query also failed: {e2}")
            return []

@router.patch("/attendance/{attendance_id}")
def update_attendance_status(
    attendance_id: str,
    status: str,
    db = Depends(get_db),
    current_user: schemas.User = Depends(teacher_required)
):
    attendance_ref = db.collection("attendance").document(attendance_id)
    attendance_doc = attendance_ref.get()
    
    if not attendance_doc.exists:
        raise HTTPException(status_code=404, detail="Attendance record not found")
        
    att_data = attendance_doc.to_dict()
    student_id = att_data.get("student_id")
    
    student_doc = db.collection("students").document(student_id).get()
    if student_doc.exists and student_doc.to_dict().get("mentor_id") != current_user.id:
         raise HTTPException(status_code=403, detail="You can only change attendance for your mentored students")
         
    attendance_ref.update({"status": status})
    return {"message": "Attendance status updated", "new_status": status}

@router.post("/attendance/approve")
def approve_attendance(
    db = Depends(get_db),
    current_user: schemas.User = Depends(teacher_required)
):
    students = db.collection("students").where("mentor_id", "==", current_user.id).get()
    student_ids = [s.id for s in students]
    
    if not student_ids:
        return {"message": "No students to approve"}
        
    batch = db.batch()
    
    for s_id in student_ids:
        unapproved_docs = db.collection("attendance").where("student_id", "==", s_id).where("is_approved", "==", False).get()
        for doc in unapproved_docs:
            batch.update(doc.reference, {"is_approved": True})
            
    batch.commit()
    return {"message": "Attendance sheet approved"}

@router.get("/attendance/export")
def export_attendance_csv(
    db = Depends(get_db),
    current_user: schemas.User = Depends(teacher_required)
):
    students_docs = db.collection("students").where("mentor_id", "==", current_user.id).get()
    student_map = {doc.id: doc.to_dict() for doc in students_docs}
    student_ids = list(student_map.keys())
    
    if not student_ids:
        raise HTTPException(status_code=404, detail="No mentored students found")
        
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Name", "Roll Number", "Course", "Status", "Time", "Confidence Score", "Approved"])
    
    for s_id in student_ids:
        records = db.collection("attendance").where("student_id", "==", s_id).where("is_approved", "==", True).get()
        student_data = student_map[s_id]
        for record_doc in records:
            record = record_doc.to_dict()
            writer.writerow([
                s_id,
                student_data.get("name"),
                student_data.get("roll_number"),
                student_data.get("course"),
                record.get("status"),
                record.get("timestamp").isoformat() if hasattr(record.get("timestamp"), 'isoformat') else record.get("timestamp"),
                f"{record.get('verification_score', 0.0):.2f}",
                record.get("is_approved")
            ])
            
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()), 
        media_type="text/csv", 
        headers={"Content-Disposition": f"attachment; filename=approved_attendance_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@router.delete("/attendance/reset")
def reset_attendance(
    db = Depends(get_db),
    current_user: schemas.User = Depends(teacher_required)
):
    try:
        def delete_collection(coll_ref, batch_size):
            docs = coll_ref.limit(batch_size).get()
            deleted = 0
            for doc in docs:
                doc.reference.delete()
                deleted += 1
            if deleted >= batch_size:
                return delete_collection(coll_ref, batch_size)
        
        delete_collection(db.collection("attendance"), 100)
        
        return {"message": "All attendance records cleared successfully."}
    except Exception as e:
        print(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail="Database reset failed.")
