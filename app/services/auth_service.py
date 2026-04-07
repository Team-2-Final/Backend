from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.oracle.user import User
from app.models.token.refresh_token import RefreshToken
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def signup_user(db: Session, username: str, email: str, password: str):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return None

    new_user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role="USER",
        created_at=datetime.now()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def login_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    refresh_token_row = RefreshToken(
        user_id=user.id,
        refresh_token=refresh_token,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(days=7),
        revoked=0,
    )

    db.add(refresh_token_row)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def refresh_access_token(db: Session, refresh_token: str):
    payload = decode_token(refresh_token)
    if not payload:
        return None

    if payload.get("type") != "refresh":
        return None

    email = payload.get("sub")
    if not email:
        return None

    token_in_db = (
        db.query(RefreshToken)
        .filter(RefreshToken.refresh_token == refresh_token)
        .first()
    )

    if not token_in_db:
        return None

    if token_in_db.revoked == 1:
        return None

    now = datetime.now()
    if token_in_db.expires_at < now:
        return None

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None

    new_access_token = create_access_token({"sub": user.email})

    return {
        "access_token": new_access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }