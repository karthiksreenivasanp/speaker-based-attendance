from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, PickleType, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base

class UserRole(enum.Enum):
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole), default=UserRole.STUDENT)
    
    # Relationships based on role
    student_profile = relationship("Student", foreign_keys="Student.user_id", back_populates="user", uselist=False)
    # If teacher, they can have many students as mentor
    mentored_students = relationship("Student", foreign_keys="Student.mentor_id", back_populates="mentor")
    classes_taught = relationship("ClassSession", back_populates="teacher")

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Selected Teacher
    
    name = Column(String, index=True)
    roll_number = Column(String, unique=True, index=True)
    course = Column(String)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="student_profile")
    mentor = relationship("User", foreign_keys=[mentor_id], back_populates="mentored_students")
    voice_templates = relationship("VoiceTemplate", back_populates="student")
    attendance_records = relationship("Attendance", back_populates="student")

class VoiceTemplate(Base):
    __tablename__ = "voice_templates"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    embedding = Column(PickleType) # Storing numpy array as bytes/pickle
    enrollment_date = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("Student", back_populates="voice_templates")

class ClassSession(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date = Column(String) # YYYY-MM-DD
    time = Column(String) # HH:MM
    session_start = Column(DateTime, nullable=True) # When teacher sets the location
    room = Column(String)
    
    # Geofencing coordinates (Classroom center)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius = Column(Float, default=20.0) # Allowed radius in meters
    
    teacher = relationship("User", back_populates="classes_taught")
    attendance_records = relationship("Attendance", back_populates="class_session")

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    class_id = Column(Integer, ForeignKey("classes.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String) # PRESENT, LATECOMER, ABSENT, REJECTED
    is_approved = Column(Boolean, default=False) # Marked by teacher
    
    verification_score = Column(Float)
    liveness_score = Column(Float)
    
    # Location where attendance was marked
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    student = relationship("Student", back_populates="attendance_records")
    class_session = relationship("ClassSession", back_populates="attendance_records")
