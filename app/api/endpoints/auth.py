from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from app.db.database import get_db
from app import schemas
from app.core import security
from app.core.config import settings

router = APIRouter()

@router.post("/register", response_model=schemas.User)
def register_user(user_in: schemas.UserCreate, db = Depends(get_db)):
    users_ref = db.collection("users")
    doc_ref = users_ref.document(user_in.username)
    if doc_ref.get().exists:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    
    hashed_password = security.get_password_hash(user_in.password)
    user_data = {
        "username": user_in.username,
        "hashed_password": hashed_password,
        "role": user_in.role.value
    }
    doc_ref.set(user_data)
    
    # If student, create student profile
    if user_in.role == schemas.UserRole.STUDENT:
        student_data = {
            "user_id": user_in.username,
            "name": user_in.name or user_in.username,
            "roll_number": user_in.roll_number or f"TEMP_{user_in.username}",
            "course": user_in.course or "DEFAULT",
            "mentor_id": None
        }
        db.collection("students").document(user_in.username).set(student_data)
        
    return schemas.User(
        id=user_in.username,
        username=user_in.username,
        role=user_in.role
    )

@router.post("/login", response_model=schemas.Token)
def login(db = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user_doc = db.collection("users").document(form_data.username).get()
    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_data = user_doc.to_dict()
    if not security.verify_password(form_data.password, user_data.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    role_str = user_data.get("role", "STUDENT")
    
    return {
        "access_token": security.create_access_token(
            form_data.username, role=role_str, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
        "role": getattr(schemas.UserRole, role_str.upper(), schemas.UserRole.STUDENT),
        "user_id": user_doc.id
    }
