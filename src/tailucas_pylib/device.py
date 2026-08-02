from typing import Annotated

from pydantic import BaseModel, Field


class Device(BaseModel):  # type: ignore[misc]
    active: bool | None = None
    device_id: str | None = None
    device_key: str
    device_label: str | None = None
    device_params: str | None = None
    device_type: str
    event_detail: str | None = None
    group_name: str | None = None
    image: bytes | None = None
    image_timestamp: str | None = None
    input_label: str | None = None
    input_location: str | None = None
    is_input: bool | None = None
    is_output: bool | None = None
    last_metered_minute: float | None = None
    last_minute_metered: int | None = None
    last_sample_value: int | None = None
    location: str | None = None
    name: str | None = None
    normal_value: int | None = None
    pulse_discards: int | None = None
    register_reading: int | None = None
    sample_value: int | None = None
    storage_path: str | None = None
    storage_url: str | None = None
    timestamp: int | None = None
    type_: Annotated[str | None, Field(alias="type")] = None
    uptime: int | None = None

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
