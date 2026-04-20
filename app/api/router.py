from fastapi import APIRouter
from app.api import analysis, environment, auth, control

router = APIRouter()

# 이미지 분석(ai)
router.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["analysis"]
)

# 환경정보 저장
router.include_router(
    environment.router,
    prefix="/environment",
    tags=["environment"]
)

# 회원가입, 로그인
router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"]
)

# 기능 컨트롤
router.include_router(
    control.router,
    prefix="/control",
    tags=["control"]
)
