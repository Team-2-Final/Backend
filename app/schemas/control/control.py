# app/schemas/control/device_control.py

from pydantic import BaseModel
from typing import Literal


class DeviceModeRequest(BaseModel):
    device: str   # "heater", "fan" ...
    mode: Literal["auto", "manual"]


class DeviceTargetRequest(BaseModel):
    device: str
    value: float