from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"

# User Schemas
class UserBase(BaseModel):
    username: str
    role: UserRole

class UserCreate(UserBase):
    password: str
    name: Optional[str] = None
    roll_number: Optional[str] = None
    course: Optional[str] = None

class User(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
    role: UserRole
    user_id: int

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None

# Login Schema
class LoginRequest(BaseModel):
    username: str
    password: str

# Student Schemas
class StudentBase(BaseModel):
    name: str
    roll_number: str
    course: str
    mentor_id: Optional[int] = None

class StudentCreate(StudentBase):
    user_id: int

class Student(StudentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Attendance Schemas
class AttendanceBase(BaseModel):
    student_id: int
    class_id: int
    status: str

class AttendanceCreate(AttendanceBase):
    verification_score: float
    liveness_score: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class Attendance(AttendanceBase):
    id: int
    timestamp: datetime
    verification_score: float
    liveness_score: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_approved: bool
    model_config = ConfigDict(from_attributes=True)

# Class Session Schemas
class ClassLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    radius: Optional[float] = 20.0

class ClassSession(BaseModel):
    id: int
    course_id: str
    teacher_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: float
    session_start: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# Response Schemas
class VerificationResponse(BaseModel):
    verified: bool
    score: float
    liveness_score: float
    student_id: Optional[int] = None
    message: str
    location_verified: bool = True
