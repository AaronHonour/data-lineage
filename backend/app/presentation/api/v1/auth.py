"""
Authentication API endpoints.

Simple authentication for demo purposes.
In production, use proper user management, password hashing, etc.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

# Simple in-memory user store for demo
# In production, use a proper database with hashed passwords
DEMO_USERS = {
    "admin": {
        "username": "admin",
        "password": "admin",  # In production: hash this!
        "email": "admin@lineage.local",
        "full_name": "Admin User",
    },
    "demo": {
        "username": "demo",
        "password": "demo",
        "email": "demo@lineage.local",
        "full_name": "Demo User",
    },
}

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production-use-env-variable"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

router = APIRouter(prefix="/auth", tags=["authentication"])


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    user: dict


class User(BaseModel):
    """User model."""
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = DEMO_USERS.get(username)
    if user is None:
        raise credentials_exception

    return user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login endpoint.

    Returns JWT token for valid credentials.
    Demo credentials: admin/admin or demo/demo
    """
    user = DEMO_USERS.get(form_data.username)

    if not user or user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["username"],
            "username": user["username"],
            "email": user.get("email"),
            "full_name": user.get("full_name"),
        },
    }


@router.get("/me", response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user.
    """
    return {
        "id": current_user["username"],
        "username": current_user["username"],
        "email": current_user.get("email"),
        "full_name": current_user.get("full_name"),
    }
