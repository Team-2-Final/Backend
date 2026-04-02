from fastapi import APIRouter
from app.schemas.data import SensorData
from app.services.data_service import DataService

router = APIRouter()

data_service = DataService()

@router.post("/data")
def receive_data(data: SensorData):
    result = data_service.process(data.dict())
    return result