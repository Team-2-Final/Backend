from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.data_service import DataService
from app.services.dashboard_service import DashboardService
from app.db.oracle import get_oracle_db

router = APIRouter()
data_service = DataService()
dashboard_service = DashboardService()

# 1. 기존 AI 분석 기능 (유지)
@router.post("/inference")
async def inference(
    batch_id: int = Form(...),
    image: UploadFile = File(...)
):
    result = await data_service.process(
        batch_id=batch_id,
        image_file=image
    )
    return result

# 2. 작기 목록 가져오기 (프론트엔드 드롭다운용 추가)
@router.get("/growth-batch")
def get_batches(db: Session = Depends(get_oracle_db)):
    result = db.execute(text("SELECT id, crop_type, description FROM growth_batch ORDER BY id DESC")).mappings().all()
    return result

# 3. 대시보드 종합 데이터 가져오기 (프론트엔드 차트용 추가)
@router.get("/dashboard/{batch_id}")
def get_dashboard_api(batch_id: int):
    # 백엔드의 data_service에서 대시보드 데이터 조립 함수 호출
    return dashboard_service.get_dashboard(batch_id)

@router.get("/stats/{batch_id}")
def get_stats(
    batch_id: int,
    range_type: str = "hour",   # hour | day | week
    db: Session = Depends(get_oracle_db)
):
    print("🔥 stats API 들어옴", batch_id, range_type)
    if range_type == "hour":

        query = """
        SELECT
            TO_CHAR(recorded_at, 'HH24') AS label,
            AVG(temperature) AS temperature,
            AVG(humidity) AS humidity,
            AVG(co2) AS co2
        FROM environment_data
        WHERE batch_id = :batch_id
          AND recorded_at >= SYSDATE - (1/24)
        GROUP BY TO_CHAR(recorded_at, 'HH24')
        ORDER BY label
        """

    elif range_type == "day":
        query = """
        SELECT
            TO_CHAR(recorded_at, 'HH24') AS label,
            AVG(temperature) AS temperature,
            AVG(humidity) AS humidity,
            AVG(co2) AS co2
        FROM environment_data
        WHERE batch_id = :batch_id
          AND recorded_at >= TRUNC(SYSDATE)
        GROUP BY TO_CHAR(recorded_at, 'HH24')
        ORDER BY label
        """

    elif range_type == "week":
        query = """
        SELECT
            TO_CHAR(TRUNC(recorded_at), 'YYYY-MM-DD') AS label,
            AVG(temperature) AS temperature,
            AVG(humidity) AS humidity,
            AVG(co2) AS co2
        FROM environment_data
        WHERE batch_id = :batch_id
          AND recorded_at >= SYSDATE - 7
        GROUP BY TRUNC(recorded_at)
        ORDER BY label
        """

    else:
        return {"error": "invalid range_type"}

    result = db.execute(text(query), {"batch_id": batch_id}).mappings().all()
    return list(result)
