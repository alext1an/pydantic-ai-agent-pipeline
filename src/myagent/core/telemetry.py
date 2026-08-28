#/src/myagent/core/telemetry.py
from urllib.parse import urlparse

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_OTLP_SPANS = "/v1/traces"


def _traces_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    return f"{parsed.scheme}://{parsed.netloc}{_OTLP_SPANS}"


def init_telemetry(endpoint: str) -> None:
    """Send pydantic-ai traces to Arize Phoenix when PHOENIX_COLLECTOR_ENDPOINT is set."""
    if not endpoint:
        return
    provider = TracerProvider(
        resource=Resource.create({"service.name": "myagent"}),
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=_traces_endpoint(endpoint)))
    )
    trace.set_tracer_provider(provider)


def _self_check() -> None:
    assert _traces_endpoint("http://localhost:6006") == "http://localhost:6006/v1/traces"
    assert _traces_endpoint("http://localhost:6006/v1/traces") == "http://localhost:6006/v1/traces"
    assert _traces_endpoint("http://localhost:6006/v0/traces") == "http://localhost:6006/v1/traces"


if __name__ == "__main__":
    _self_check()