"""Authenticated HTTP service for the free-tier-first AI router."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from openai_compatible import OpenAICompatibleAdapter
from router import ProviderRouter, TaskRequest, load_registry
from security import SlidingWindowRateLimiter, bearer_authorized
from sqlite_store import SQLiteTaskStore

REGISTRY_PATH = os.environ.get("AI_REGISTRY_PATH", "providers.json")
DATABASE_PATH = os.environ.get("AI_TASK_DB", "data/tasks.sqlite3")
SERVICE_TOKEN = os.environ.get("SERVICE_BEARER_TOKEN", "")
MAX_BODY_BYTES = 128 * 1024
RATE_LIMIT = SlidingWindowRateLimiter(
    limit=max(1, int(os.environ.get("REQUESTS_PER_MINUTE", "60"))),
    window_seconds=60,
)


def build_router():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    providers = load_registry(data)
    providers_by_id = {p.provider_id: p for p in providers}
    adapters = {}
    for item in data.get("providers", []):
        if not item.get("enabled", False):
            continue
        base_url = item.get("base_url")
        env_name = item.get("credential_env")
        if not base_url or not env_name:
            continue
        if item.get("adapter") == "openai_compatible":
            adapters[item["id"]] = OpenAICompatibleAdapter(
                base_url, env_name, extra_headers=item.get("headers", {})
            )
            providers_by_id[item["id"]].authenticated = bool(os.environ.get(env_name))
    return ProviderRouter(providers, adapters, task_store=SQLiteTaskStore(DATABASE_PATH))


ROUTER = None


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok", "service": "infinite-ai-power-os-500"})
        self._send(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/v1/generate":
            return self._send(404, {"error": "not_found"})
        if not bearer_authorized(self.headers.get("Authorization", ""), SERVICE_TOKEN):
            return self._send(401 if SERVICE_TOKEN else 503,
                              {"error": "unauthorized" if SERVICE_TOKEN else "service_auth_not_configured"})
        client_key = self.client_address[0]
        if not RATE_LIMIT.allow(client_key):
            return self._send(429, {"error": "request_rate_limited"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return self._send(400, {"error": "empty_body"})
            if length > MAX_BODY_BYTES:
                return self._send(413, {"error": "payload_size_invalid"})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("input", {}), dict):
                return self._send(400, {"error": "invalid_request_shape"})
            capability = str(payload.get("capability", "text"))
            max_failovers = max(0, min(int(payload.get("max_failovers", 5)), 10))
            request = TaskRequest(
                capability=capability,
                payload=payload.get("input", {}),
                allowed_cost_tiers=("free",),
                max_failovers=max_failovers,
            )
            result = ROUTER.route(request)
            status = 200 if result.status.value == "succeeded" else 503
            return self._send(status, {
                "status": result.status.value,
                "task_id": result.task_id,
                "provider_id": result.provider_id,
                "output": result.output,
                "attempts": result.attempts,
                "message": result.message,
            })
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            return self._send(400, {"error": "invalid_json_or_fields"})

    def log_message(self, fmt, *args):
        print("http", self.address_string(), fmt % args)


def main():
    global ROUTER
    if not SERVICE_TOKEN:
        raise RuntimeError("Set SERVICE_BEARER_TOKEN before starting the service")
    ROUTER = build_router()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
