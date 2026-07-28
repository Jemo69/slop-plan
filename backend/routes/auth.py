import secrets
from fastapi import APIRouter, HTTPException, Header, Cookie, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, ValidationError
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
async def register(request: Request):
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
            req = RegisterRequest(**body)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
    else:
        try:
            form_data = await request.form()
            req = RegisterRequest(email=form_data.get("email", ""), password=form_data.get("password", ""))
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())

    existing = await User.filter(email=req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    api_key = generate_api_key()
    password_hash = hash_password(req.password)
    user = await User.create(email=req.email, api_key=api_key, password_hash=password_hash)

    resp = JSONResponse(
        content=AuthResponse(
            api_key=user.api_key,
            email=user.email,
            user_id=str(user.id),
            has_password=True,
        ).model_dump(),
        status_code=201,
    )
    resp.set_cookie(key="plan_api_key", value=api_key, httponly=True, samesite="lax")
    return resp


@router.post("/login", response_model=AuthResponse)
async def login(request: Request):
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
            req = LoginRequest(**body)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
    else:
        try:
            form_data = await request.form()
            req = LoginRequest(email=form_data.get("email", ""), password=form_data.get("password", ""))
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())

    user = await User.filter(email=req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.password_hash:
        raise HTTPException(status_code=400, detail="Account has no password set")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")

    resp = JSONResponse(
        content=AuthResponse(
            api_key=user.api_key,
            email=user.email,
            user_id=str(user.id),
            has_password=True,
        ).model_dump(),
    )
    resp.set_cookie(key="plan_api_key", value=user.api_key, httponly=True, samesite="lax")
    return resp


@router.post("/logout")
async def logout():
    resp = JSONResponse(content={"status": "logged_out"})
    resp.delete_cookie(key="plan_api_key")
    return resp