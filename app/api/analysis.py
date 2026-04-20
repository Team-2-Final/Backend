from fastapi import APIRouter, UploadFile, File, Form
from app.services.data_service import DataService

router = APIRouter()
data_service = DataService()


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