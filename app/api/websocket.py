from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import ws_manager
from app.services.dashboard_service import DashboardService

router = APIRouter()
dashboard_service = DashboardService()


@router.websocket("/ws/dashboard/{batch_id}")
async def dashboard_websocket(websocket: WebSocket, batch_id: int):
    await ws_manager.connect(batch_id, websocket)

    try:
        await websocket.send_json({
            "type": "dashboard_init",
            "data": dashboard_service.get_dashboard(batch_id)
        })

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(batch_id, websocket)