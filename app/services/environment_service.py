from datetime import datetime
from app.db.oracle import SessionLocal
from app.models.oracle.environment_data import EnvironmentData
from app.schemas.environment.environment import EnvironmentCreate

class EnvironmentService:

    async def save(self, batch_id: int, data: EnvironmentCreate):
        db = SessionLocal()

        db.add(EnvironmentData(
            batch_id=batch_id,
            temperature=data.temperature,
            humidity=data.humidity,
            co2=data.co2,
            radiation=data.radiation,
            soil_ec=data.soil_ec,
            soil_moisture=data.soil_moisture,
            ph=data.ph,
        ))

        db.commit()
        db.close()

        return {"status": "ok"}