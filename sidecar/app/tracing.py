"""Optional OpenTelemetry tracing for reserve/settle hot paths."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger(__name__)

_tracer = None
_initialized = False


def setup_tracing(*, service_name: str, otlp_endpoint: str | None) -> None:
    global _tracer, _initialized
    if _initialized:
        return
    _initialized = True
    if not otlp_endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces"))
        )
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("modelgovernor.sidecar")
        logger.info("opentelemetry tracing enabled endpoint=%s", otlp_endpoint)
    except ImportError:
        logger.info("opentelemetry packages not installed; tracing disabled")
    except Exception as exc:
        logger.warning("failed to initialize tracing: %s", exc)


@contextmanager
def span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name) as current:
        if attributes:
            for key, value in attributes.items():
                if value is not None:
                    current.set_attribute(key, value)
        yield current
