import pytest

pytest.importorskip("pydantic", reason="requires the 'dto' extra")


def test_device_required_fields_only():
    """Test Device creation with only required fields."""
    from tailucas_pylib.device import Device

    device = Device(device_key="key-001", device_type="thermometer")
    assert device.device_key == "key-001"
    assert device.device_type == "thermometer"
    assert device.active is None
    assert device.device_id is None


def test_device_with_optional_fields():
    """Test Device creation with all optional fields."""
    from tailucas_pylib.device import Device

    device = Device(
        active=True,
        device_id="dev-123",
        device_key="key-001",
        device_label="Living Room",
        device_type="thermometer",
        group_name="indoor",
        name="temp-sensor-1",
    )
    assert device.active is True
    assert device.device_id == "dev-123"
    assert device.device_label == "Living Room"
    assert device.group_name == "indoor"
    assert device.name == "temp-sensor-1"


def test_device_with_image_bytes():
    """Test Device creation with image as bytes and __str__ formatting."""
    from tailucas_pylib.device import Device

    device = Device(
        device_key="key-001",
        device_type="camera",
        image=b"fake-image-data",
    )
    str_repr = str(device)
    assert "image=15 bytes" in str_repr


def test_device_str_no_bytes():
    """Test __str__ output when there are no bytes fields."""
    from tailucas_pylib.device import Device

    device = Device(
        device_key="key-001",
        device_type="sensor",
        name="test-device",
        active=True,
        sample_value=42,
    )
    str_repr = str(device)
    assert "device_key=key-001" in str_repr
    assert "device_type=sensor" in str_repr
    assert "active=True" in str_repr
    assert "sample_value=42" in str_repr
    assert "name=test-device" in str_repr


def test_device_defaults():
    """Test Device default values are None for optional fields."""
    from tailucas_pylib.device import Device

    device = Device(device_key="key-001", device_type="sensor")
    assert device.active is None
    assert device.device_id is None
    assert device.image is None
    assert device.sample_value is None
    assert device.name is None
    assert device.timestamp is None
