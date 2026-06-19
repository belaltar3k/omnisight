import urllib.request
import urllib.error
import json

# Configuration
GATEWAY_URL = "http://localhost:3000"
ANALYTICS_URL = "http://localhost:3006"
TOKEN = ""  # refreshed at runtime

def get_token():
    login_payload = json.dumps({"identifier": "admin@omnisight.com", "password": "Admin123!"}).encode()
    req = urllib.request.Request(
        f"{GATEWAY_URL}/api/v1/auth/login",
        data=login_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["data"]["accessToken"]


def build_endpoints(token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return [
        # ── Existing analytics endpoints (via gateway) ─────────────────────────
        {
            "name": "Dashboard Summary",
            "method": "GET",
            "url": f"{GATEWAY_URL}/api/v1/analytics/dashboard/",
            "headers": headers,
        },
        {
            "name": "Incident Stats",
            "method": "GET",
            "url": f"{GATEWAY_URL}/api/v1/analytics/incidents/stats",
            "headers": headers,
        },
        {
            "name": "Incident Trends",
            "method": "GET",
            "url": f"{GATEWAY_URL}/api/v1/analytics/incidents/trends",
            "headers": headers,
        },
        {
            "name": "Response Times Stats",
            "method": "GET",
            "url": f"{GATEWAY_URL}/api/v1/analytics/incidents/response-times",
            "headers": headers,
        },
        {
            "name": "Camera Performance",
            "method": "GET",
            "url": f"{GATEWAY_URL}/api/v1/analytics/cameras/performance",
            "headers": headers,
        },
        {
            "name": "Spatial Heatmap",
            "method": "GET",
            "url": f"{GATEWAY_URL}/api/v1/analytics/heatmap/",
            "headers": headers,
        },
        {
            "name": "Generate CSV Report",
            "method": "POST",
            "url": f"{GATEWAY_URL}/api/v1/analytics/reports/generate",
            "headers": headers,
            "body": {
                "report_type": "incident_summary",
                "date_from": "2026-06-01T00:00:00.000Z",
                "date_to": "2026-06-30T00:00:00.000Z",
            },
        },
        # ── Surveillance analytics endpoints (direct to analytics-service) ─────
        {
            "name": "SA — Latest Snapshot",
            "method": "GET",
            "url": f"{ANALYTICS_URL}/api/v1/analytics/surveillance/latest",
            "headers": {"Content-Type": "application/json"},
        },
        {
            "name": "SA — Crowd (last 1h)",
            "method": "GET",
            "url": f"{ANALYTICS_URL}/api/v1/analytics/surveillance/crowd?hours=1",
            "headers": {"Content-Type": "application/json"},
        },
        {
            "name": "SA — Traffic (last 1h)",
            "method": "GET",
            "url": f"{ANALYTICS_URL}/api/v1/analytics/surveillance/traffic?hours=1",
            "headers": {"Content-Type": "application/json"},
        },
        {
            "name": "SA — Full Summary",
            "method": "GET",
            "url": f"{ANALYTICS_URL}/api/v1/analytics/surveillance/summary",
            "headers": {"Content-Type": "application/json"},
        },
    ]

def run_tests():
    print("==================================================")
    print("      Omnisight Analytics Endpoints Test         ")
    print("==================================================")

    print("\nLogging in to get fresh JWT token...")
    try:
        token = get_token()
        print(f"Token obtained: {token[:40]}...")
    except Exception as e:
        print(f"Login failed: {e}")
        return

    endpoints = build_endpoints(token)
    success_count = 0

    for endpoint in endpoints:
        name = endpoint["name"]
        method = endpoint["method"]
        url = endpoint["url"]
        hdrs = endpoint.get("headers", {})

        print(f"\n[Test] {name}")
        print(f"       {method} {url}")

        req = urllib.request.Request(url, headers=hdrs, method=method)

        if "body" in endpoint:
            data = json.dumps(endpoint["body"]).encode("utf-8")
            req.data = data

        try:
            with urllib.request.urlopen(req) as response:
                status = response.status
                body = response.read()
                print(f"       Status: {status} OK")
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    res_json = json.loads(body.decode("utf-8"))
                    data_part = res_json.get("data") if isinstance(res_json, dict) and "data" in res_json else res_json
                    snippet = json.dumps(data_part, indent=2)
                    lines = snippet.split("\n")
                    preview = "\n".join(lines[:30])
                    if len(lines) > 30:
                        preview += f"\n       ... ({len(lines) - 30} more lines)"
                    for line in preview.split("\n"):
                        print(f"       {line}")
                else:
                    print(f"       Binary response: {len(body)} bytes")
                success_count += 1

        except urllib.error.HTTPError as e:
            print(f"       FAILED ({e.code}): {e.read().decode('utf-8', errors='replace')[:200]}")
        except urllib.error.URLError as e:
            print(f"       UNREACHABLE: {e.reason}")

    print("\n==================================================")
    print(f" Completed: {success_count}/{len(endpoints)} passed")
    print("==================================================")


if __name__ == "__main__":
    run_tests()
