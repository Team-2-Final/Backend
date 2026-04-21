from fastapi import APIRouter
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
dashboard_service = DashboardService()


@router.get("/{batch_id}")
def get_dashboard(batch_id: int):
    return dashboard_service.get_dashboard(batch_id)


@router.get("/{batch_id}/overview")
def get_overview(batch_id: int):
    return dashboard_service.get_overview(batch_id)


@router.get("/{batch_id}/sensors")
def get_sensors(batch_id: int):
    return dashboard_service.get_latest_sensors(batch_id)


@router.get("/{batch_id}/crop-status")
def get_crop_status(batch_id: int):
    return dashboard_service.get_crop_status(batch_id)


@router.get("/{batch_id}/device-logs")
def get_device_logs(batch_id: int):
    return dashboard_service.get_device_logs(batch_id)


@router.get("/{batch_id}/ai-reports")
def get_ai_reports(batch_id: int):
    return dashboard_service.get_ai_reports(batch_id)


@router.get("/{batch_id}/cctv")
def get_cctv(batch_id: int):
    return dashboard_service.get_cctv_status(batch_id)