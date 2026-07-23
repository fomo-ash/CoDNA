# OpenTelemetry & SigNoz Observability Guide

CoDNA is fully instrumented with OpenTelemetry (OTel) to export distributed traces, performance metrics, and logs to **SigNoz** (or any OTLP-compliant observability platform).

---

## 🚀 Usage & Setup Options

### Option 1: Connecting to Local/Existing SigNoz (Default)
If you already have SigNoz running locally on ports `4317`/`4318`:
- CoDNA services are pre-configured to export OTLP traces to `http://host.docker.internal:4318`.
- Access your local SigNoz UI at [`http://localhost:8080`](http://localhost:8080).

### Option 2: Dedicated SigNoz via Docker Compose
To launch a dedicated ClickHouse + SigNoz stack alongside CoDNA:

```bash
docker-compose -f docker-compose.yml -f infra/docker/docker-compose.signoz.yml up -d
```

### Accessing Services

| Service | URL | Description |
| :--- | :--- | :--- |
| **SigNoz Dashboard** | [`http://localhost:8080`](http://localhost:8080) (or `http://localhost:3301`) | APM, Traces, Metrics & Logs UI |
| **Web Frontend** | [`http://localhost:3333`](http://localhost:3333) | Next.js Frontend |
| **FastAPI Backend** | [`http://localhost:8001/docs`](http://localhost:8001/docs) | API Swagger Documentation |
| **OTel Collector (OTLP gRPC)** | `localhost:4317` | OpenTelemetry Collector gRPC Port |
| **OTel Collector (OTLP HTTP)** | `localhost:4318` | OpenTelemetry Collector HTTP Port |

---

## 🔍 How Instrumentation Works

### 1. Python FastAPI Backend (`apps/api`)
- **File**: [`apps/api/app/core/telemetry.py`](file:///c:/Users/ASHUTOSH/CoDNA/CoDNA/apps/api/app/core/telemetry.py)
- **Instrumented Components**:
  - **Traces**: FastAPI Route Requests, SQLAlchemy Async Queries, Redis Operations, and HTTPX Requests.
  - **Logs**: OpenTelemetry `LoggingHandler` is attached to Python's standard `logging` framework, forwarding `logger.info()`, `logger.error()`, and exception tracebacks directly to SigNoz `/v1/logs`.

### 2. Next.js Web Frontend (`apps/web`)
- **File**: [`apps/web/instrumentation.ts`](file:///c:/Users/ASHUTOSH/CoDNA/CoDNA/apps/web/instrumentation.ts)
- **Instrumented Components**:
  - Server-Side Rendering (SSR) and API route handlers
  - Node.js SDK auto-instrumentation

---

## 🛠️ Environment Configuration

Set the following variables in your `.env` file or environment:

```env
# OpenTelemetry Configuration
OTEL_SERVICE_NAME=codna-api
OTEL_WEB_SERVICE_NAME=codna-web
OTEL_WORKER_SERVICE_NAME=codna-worker
OTEL_EXPORTER_OTLP_ENDPOINT=http://signoz-otel-collector:4318
```

---

## ☁️ Deployment Guide (Deploying SigNoz to Production)

When deploying to production (e.g., AWS, GCP, Azure, or Kubernetes):

### Option A: Using SigNoz Cloud
1. Sign up for a [SigNoz Cloud](https://signoz.io/cloud/) account.
2. Obtain your **Ingestion Key** and **OTLP Region Endpoint** (e.g., `ingest.us.signoz.cloud:443`).
3. Update your production environment variables:
   ```env
   OTEL_EXPORTER_OTLP_ENDPOINT=https://ingest.us.signoz.cloud:443
   OTEL_EXPORTER_OTLP_HEADERS=signoz-access-token=<YOUR_SIGNOZ_INGESTION_KEY>
   ```

### Option B: Self-Hosted Production SigNoz (EC2 / VM)
1. Deploy SigNoz using the official production install script on your VM:
   ```bash
   git clone -b main https://github.com/SigNoz/signoz.git && cd signoz/deploy/
   ./install.sh
   ```
2. Point your CoDNA services' `OTEL_EXPORTER_OTLP_ENDPOINT` to your VM's public or internal domain/IP (port `4318` for HTTP or `4317` for gRPC).
