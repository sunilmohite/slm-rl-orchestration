"""
Minimal SLM inference service.
- Serves text generation using a small HuggingFace model (distilgpt2, ~350MB, CPU-friendly).
- Exposes /generate for inference requests.
- Exposes /metrics in Prometheus format (request rate, latency, in-flight requests).
- Exposes /healthz and /readyz for OpenShift probes.

This plays the role your dissertation calls the "AI Inference Service" / "SLM".
"""
import time
import os
from flask import Flask, request, jsonify, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

MODEL_NAME = os.environ.get("MODEL_NAME", "distilgpt2")

app = Flask(__name__)

# ---- Prometheus metrics ----
REQUEST_COUNT = Counter("slm_requests_total", "Total inference requests")
REQUEST_LATENCY = Histogram(
    "slm_request_latency_seconds",
    "Inference request latency",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
IN_FLIGHT = Gauge("slm_requests_in_flight", "Requests currently being processed")

# ---- Lazy model load (so /healthz responds immediately at pod start) ----
_generator = None


def get_generator():
    global _generator
    if _generator is None:
        from transformers import pipeline

        print(f"Loading model {MODEL_NAME} ...", flush=True)
        _generator = pipeline("text-generation", model=MODEL_NAME, device=-1)
        print("Model loaded.", flush=True)
    return _generator


@app.route("/healthz")
def healthz():
    return "ok", 200


@app.route("/readyz")
def readyz():
    # Only ready once model is loaded, so k8s doesn't send traffic too early.
    return ("ready", 200) if _generator is not None else ("loading", 503)


@app.route("/generate", methods=["POST"])
def generate():
    IN_FLIGHT.inc()
    start = time.time()
    try:
        payload = request.get_json(force=True) or {}
        prompt = payload.get("prompt", "The future of AI is")
        max_new_tokens = int(payload.get("max_new_tokens", 20))

        gen = get_generator()
        output = gen(prompt, max_new_tokens=max_new_tokens, num_return_sequences=1)

        REQUEST_COUNT.inc()
        return jsonify({"prompt": prompt, "generated_text": output[0]["generated_text"]})
    finally:
        REQUEST_LATENCY.observe(time.time() - start)
        IN_FLIGHT.dec()


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    # Warm the model once at boot so first real request isn't a huge outlier.
    get_generator()
    app.run(host="0.0.0.0", port=8080)
