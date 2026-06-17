import secrets
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from models import User

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr


class AuthResponse(BaseModel):
    api_key: str
    email: str


def generate_api_key() -> str:
    return f"plan_{secrets.token_urlsafe(32)}"


async def get_current_user(authorization: str = Header(None)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    api_key = authorization.replace("Bearer ", "")
    user = await User.filter(api_key=api_key).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return user


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    existing = await User.filter(email=request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    api_key = generate_api_key()
    user = await User.create(email=request.email, api_key=api_key)
    
    return AuthResponse(api_key=user.api_key, email=user.email)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    user = await User.filter(email=request.email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return AuthResponse(api_key=user.api_key, email=user.email)
