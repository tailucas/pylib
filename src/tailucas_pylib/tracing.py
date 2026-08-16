import contextlib


def record_exception(exc: BaseException) -> None:
    """Record an exception on the current OpenTelemetry span.

    This is a no-op when OpenTelemetry is not installed or when the SDK is
    disabled, since the API returns no-op spans/providers in those cases.
    """
    try:
        from opentelemetry import trace
    except ImportError:
        return
    span = trace.get_current_span()
    span.set_attribute("error.type", exc.__class__.__name__)
    span.set_status(trace.Status(trace.StatusCode.ERROR))
    span.record_exception(exc)


def shutdown() -> None:
    """Shut down the OpenTelemetry providers so pending telemetry is flushed.

    Intended to be called during application shutdown so that pending telemetry
    is flushed before the process exits. Each provider is shut down defensively
    so that a partially configured or disabled SDK cannot break shutdown.
    """
    try:
        from opentelemetry import metrics, trace
        from opentelemetry._logs import get_logger_provider
    except ImportError:
        return
    with contextlib.suppress(Exception):
        trace.get_tracer_provider().shutdown()  # type: ignore[attr-defined]
    with contextlib.suppress(Exception):
        metrics.get_meter_provider().shutdown()  # type: ignore[attr-defined]
    with contextlib.suppress(Exception):
        get_logger_provider().shutdown()  # type: ignore[attr-defined]
