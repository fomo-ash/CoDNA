from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.engine import Engine

logger = logging.getLogger("app.telemetry")


def setup_telemetry(app: FastAPI | None = None, db_engine: Engine | None = None) -> None:
    """
    Initializes OpenTelemetry tracing and exports spans to SigNoz (OTLP Collector).
    Instruments FastAPI, SQLAlchemy, Redis, and HTTPX.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        service_name = os.getenv("OTEL_SERVICE_NAME", "codna-api")
        otlp_endpoint = os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://signoz-otel-collector:4318"
        )
        
        # OTLPSpanExporter for HTTP/protobuf expects /v1/traces
        traces_endpoint = otlp_endpoint.rstrip("/")
        if not traces_endpoint.endswith("/v1/traces"):
            traces_endpoint = f"{traces_endpoint}/v1/traces"

        resource = Resource.create(attributes={SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=traces_endpoint))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        # Configure OTel Log Export to SigNoz
        try:
            from opentelemetry._logs import set_logger_provider
            from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
            from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
            from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

            logs_endpoint = traces_endpoint.replace("/v1/traces", "/v1/logs")
            logger_provider = LoggerProvider(resource=resource)
            logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(OTLPLogExporter(endpoint=logs_endpoint))
            )
            set_logger_provider(logger_provider)

            # Attach OTel Handler to root logger
            handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
            logging.getLogger().addHandler(handler)
            logger.info("OpenTelemetry LoggerProvider attached to Python logging -> %s", logs_endpoint)
        except Exception as log_exc:
            logger.warning("Could not initialize OpenTelemetry log exporter: %s", log_exc)

        logger.info(
            "OpenTelemetry TracerProvider initialized for service '%s' targeting %s",
            service_name,
            traces_endpoint,
        )

        # Instrument FastAPI if app is provided
        if app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
                logger.info("FastAPI auto-instrumented with OpenTelemetry")
            except Exception as exc:
                logger.warning("Failed to instrument FastAPI with OpenTelemetry: %s", exc)

        # Instrument SQLAlchemy if db_engine is provided
        if db_engine is not None:
            try:
                from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
                target_engine = getattr(db_engine, "sync_engine", db_engine)
                SQLAlchemyInstrumentor().instrument(engine=target_engine, tracer_provider=provider)
                logger.info("SQLAlchemy engine instrumented with OpenTelemetry")
            except Exception as exc:
                logger.warning("Failed to instrument SQLAlchemy: %s", exc)

        # Instrument Redis
        try:
            from opentelemetry.instrumentation.redis import RedisInstrumentor
            RedisInstrumentor().instrument(tracer_provider=provider)
            logger.info("Redis instrumented with OpenTelemetry")
        except Exception as exc:
            logger.warning("Failed to instrument Redis: %s", exc)

        # Instrument HTTPX
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument(tracer_provider=provider)
            logger.info("HTTPX instrumented with OpenTelemetry")
        except Exception as exc:
            logger.warning("Failed to instrument HTTPX: %s", exc)

    except ImportError:
        logger.info("OpenTelemetry SDK packages not installed. Telemetry initialization skipped.")
    except Exception as exc:
        logger.error("Unexpected error during OpenTelemetry initialization: %s", exc, exc_info=True)
