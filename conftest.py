import os
import time

# Test-suite determinism: the tests assume UTC as the local timezone and the
# library's default application name, regardless of the ambient environment.
os.environ["TZ"] = "UTC"
if hasattr(time, "tzset"):  # not available on Windows
    time.tzset()
os.environ["APP_NAME"] = "test"

# Disable the OpenTelemetry SDK during tests; otherwise the gRPC exporters
# attempt to reach localhost:4317 and emit noisy "Connection refused" errors.
os.environ["OTEL_SDK_DISABLED"] = "true"

