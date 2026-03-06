from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db.database import get_db
from app import models, schemas
from app.core import security
from app.core.config import settings

router = APIRouter()

@router.post("/register", response_model=schemas.User)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    
    hashed_password = security.get_password_hash(user_in.password)
    new_user = models.User(
        username=user_in.username,
        hashed_password=hashed_password,
        role=user_in.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # If student, create student profile
    if new_user.role == models.UserRole.STUDENT:
        student = models.Student(
            user_id=new_user.id,
            name=user_in.name or new_user.username,
            roll_number=user_in.roll_number or f"TEMP_{new_user.id}",
            course=user_in.course or "DEFAULT"
        )
        db.add(student)
        db.commit()
        
    return new_user

@router.post("/login", response_model=schemas.Token)
def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.username, role=user.role.value, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id
    }
