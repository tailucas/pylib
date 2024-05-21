from typing import Optional

from pydantic import BaseModel, Field
from typing_extensions import Annotated


class Device(BaseModel):
    active: Optional[bool] = None
    device_id: Optional[str] = None
    device_key: str
    device_label: Optional[str] = None
    device_params: Optional[str] = None
    device_type: str
    event_detail: Optional[str] = None
    group_name: Optional[str] = None
    image: Optional[bytes] = None
    input_label: Optional[str] = None
    input_location: Optional[str] = None
    is_input: Optional[bool] = None
    is_output: Optional[bool] = None
    last_metered_minute: Optional[float] = None
    last_minute_metered: Optional[int] = None
    last_sample_value: Optional[int] = None
    location: Optional[str] = None
    name: Optional[str] = None
    normal_value: Optional[int] = None
    pulse_discards: Optional[int] = None
    register_reading: Optional[int] = None
    sample_value: Optional[int] = None
    storage_path: Optional[str] = None
    storage_url: Optional[str] = None
    timestamp: Optional[int] = None
    type_: Optional[Annotated[str, Field(alias="type")]] = None
    uptime: Optional[int] = None

    def __str__(self):
        str_rep = ""
        for name, value in vars(self).items():
            if len(str_rep) > 0:
                str_rep += ","
            if not isinstance(value, bytes):
                str_rep += f"{name}={value}"
            else:
                str_rep += f"{name}={len(value)} bytes"
        return str_rep
