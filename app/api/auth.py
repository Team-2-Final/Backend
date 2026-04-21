from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_email
from app.schemas.auth.auth import (
    UserSignupRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse
)
from app.services.auth_service import signup_user, login_user, refresh_access_token, logout_user, get_user_by_email
from app.db.oracle import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/signup")
def signup(request: UserSignupRequest, db: Session = Depends(get_db)):
    user = signup_user(
        db=db,
        username=request.username,
        email=request.email,
        password=request.password
    )

    if not user:
        raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")

    return {
        "message": "회원가입 성공",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }


@router.post("/login", response_model=TokenResponse)
def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    token = login_user(
        db=db,
        email=request.email,
        password=request.password
    )

    if not token:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    return token


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    token = refresh_access_token(
        db=db,
        refresh_token=request.refresh_token
    )

    if not token:
        raise HTTPException(status_code=401, detail="유효하지 않은 refresh token 입니다.")

    return token

@router.post("/logout")
def logout(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    success = logout_user(db, request.refresh_token)

    if not success:
        raise HTTPException(status_code=400, detail="이미 로그아웃 되었거나 토큰이 없습니다.")

    return {"message": "로그아웃 성공"}


@router.get("/me", response_model=UserResponse)
def me(
    email: str = Depends(get_current_email),
    db: Session = Depends(get_db)
):
    user = get_user_by_email(db, email)  # ✔ service 사용

    return user