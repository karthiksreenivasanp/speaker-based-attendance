from fastapi import APIRouter
from app.api.endpoints import students, enrollment, verification, admin, auth

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(enrollment.router, prefix="/enroll", tags=["enrollment"])
api_router.include_router(verification.router, prefix="/verify", tags=["verification"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
