from pydantic import BaseModel
from datetime import datetime

class SensorData(BaseModel):
    temperature: float
    humidity: float
    soil_moisture: float
    light: float
    timestamp: datetime