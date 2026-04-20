from pydantic import BaseModel

class EnvironmentCreate(BaseModel):
    temperature: float
    humidity: float
    co2: float
    radiation: float
    soil_ec: float
    soil_moisture: float
    ph: float