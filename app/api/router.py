from fastapi import APIRouter

router = APIRouter()

# 1번 작업 후 연결 예정
# from app.api.data import router as data_router
# from app.api.analysis import router as analysis_router
#
# router.include_router(data_router, prefix="/data", tags=["data"])
# router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])