from pydantic import BaseModel

class UserSignupRequest(BaseModel):
    username: str
    email: str
    password: str

class UserLoginRequest(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    class Config:
        from_attributes = True  # ORM → Pydantic 변환 허용