from fastapi import APIRouter
from app.api import analysis, environment, auth, control, dashboard, websocket, logget

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

# 라우터 -> 메인 라우터로 등록하는 역할
router.include_router(dashboard.router)
router.include_router(websocket.router)
router.include_router(logget.router)