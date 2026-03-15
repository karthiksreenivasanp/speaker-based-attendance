from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from app.db.database import get_db
from app import schemas
from app.core import security
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_current_user(
    db = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> schemas.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user_doc = db.collection("users").document(token_data.username).get()
    if not user_doc.exists:
        raise credentials_exception
        
    user_data = user_doc.to_dict()
    return schemas.User(**user_data, id=user_doc.id)

def get_current_active_user(
    current_user: schemas.User = Depends(get_current_user),
) -> schemas.User:
    return current_user

class RoleChecker:
    def __init__(self, allowed_roles: list[schemas.UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: schemas.User = Depends(get_current_active_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return user

# Role dependencies
teacher_required = RoleChecker([schemas.UserRole.TEACHER])
student_required = RoleChecker([schemas.UserRole.STUDENT])
