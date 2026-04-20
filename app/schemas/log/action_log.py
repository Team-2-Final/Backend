from pydantic import BaseModel
from typing import Optional, Literal


class ActionLogCreate(BaseModel):
    batch_id: int
    action_type: str
    action_mode: Literal["auto", "manual"]
    status: Literal["pending", "success", "fail"] = "pending"
    message: Optional[str] = None


class ActionResultRequest(BaseModel):
    batch_id: int
    action_id: int
    success: bool
    message: Optional[str] = None