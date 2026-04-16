from fastapi import APIRouter, HTTPException
from sqlalchemy import desc

from app.db.oracle import SessionLocal
from app.models.oracle.plant_growth import PlantGrowth

router = APIRouter()

@router.get("/latest/{batch_id}")
def get_latest_growth(batch_id: int):
    db = SessionLocal()

    try:
        latest = (
            db.query(PlantGrowth)
            .filter(PlantGrowth.batch_id == batch_id)
            .order_by(desc(PlantGrowth.recorded_at))
            .first()
        )

        if not latest:
            raise HTTPException(status_code=404, detail="생장정보가 없습니다.")

        return {
            "id": latest.id,
            "batch_id": latest.batch_id,
            "inference_id": latest.inference_id,
            "model_version": latest.model_version,
            "plant_height": latest.plant_height,
            "leaf_length": latest.leaf_length,
            "leaf_width": latest.leaf_width,
            "leaf_count": latest.leaf_count,
            "captured_at": latest.captured_at,
            "inferred_at": latest.inferred_at,
            "recorded_at": latest.recorded_at,
        }

    finally:
        db.close()