export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    try {
      const { NodeSDK } = await import("@opentelemetry/sdk-node");
      const { OTLPTraceExporter } = await import("@opentelemetry/exporter-trace-otlp-http");
      const { getNodeAutoInstrumentations } = await import(
        "@opentelemetry/auto-instrumentations-node"
      );
      const { Resource } = await import("@opentelemetry/resources");
      const { ATTR_SERVICE_NAME } = await import("@opentelemetry/semantic-conventions");

      const otlpEndpoint =
        process.env.OTEL_EXPORTER_OTLP_ENDPOINT || "http://signoz-otel-collector:4318";
      const tracesUrl = otlpEndpoint.endsWith("/v1/traces")
        ? otlpEndpoint
        : `${otlpEndpoint.replace(/\/$/, "")}/v1/traces`;

      const sdk = new NodeSDK({
        resource: new Resource({
          [ATTR_SERVICE_NAME]: process.env.OTEL_SERVICE_NAME || "codna-web",
        }),
        traceExporter: new OTLPTraceExporter({
          url: tracesUrl,
        }),
        instrumentations: [
          getNodeAutoInstrumentations({
            // Disable fs instrumentation to reduce trace noise
            "@opentelemetry/instrumentation-fs": { enabled: false },
          }),
        ],
      });

      sdk.start();
      console.log(`[OTel] Next.js instrumentation initialized for ${process.env.OTEL_SERVICE_NAME || "codna-web"} -> ${tracesUrl}`);
    } catch (err) {
      console.error("[OTel] Failed to initialize Next.js OpenTelemetry instrumentation:", err);
    }
  }
}
