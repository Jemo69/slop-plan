import secrets
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr, Field
from db import User
from services import hash_password, verify_password

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    api_key: str
    email: str
    user_id: str
    has_password: bool


def generate_api_key() -> str:
    return f"plan_{secrets.token_urlsafe(32)}"


async def get_current_user(authorization: str = Header(None)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    api_key = authorization.replace("Bearer ", "", 1).strip()
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    user = await User.filter(api_key=api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return user


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(request: RegisterRequest):
    existing = await User.filter(email=request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    api_key = generate_api_key()
    password_hash = hash_password(request.password)
    user = await User.create(email=request.email, api_key=api_key, password_hash=password_hash)

    return AuthResponse(
        api_key=user.api_key,
        email=user.email,
        user_id=str(user.id),
        has_password=True,
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    user = await User.filter(email=request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.password_hash:
        raise HTTPException(status_code=400, detail="Account has no password set")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")

    return AuthResponse(
        api_key=user.api_key,
        email=user.email,
        user_id=str(user.id),
        has_password=True,
    )