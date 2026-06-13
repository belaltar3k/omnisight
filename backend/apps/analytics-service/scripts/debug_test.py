import urllib.request
import urllib.error
import json

# Query Python FastAPI service directly on port 3006 (bypasses NestJS gateway)
LOCAL_URL = "http://localhost:3006/api/v1/analytics"

ENDPOINTS = [
    {"name": "Dashboard Summary", "url": f"{LOCAL_URL}/dashboard/"},
    {"name": "Incident Stats", "url": f"{LOCAL_URL}/incidents/stats"},
    {"name": "Incident Trends", "url": f"{LOCAL_URL}/incidents/trends"},
    {"name": "Response Times Stats", "url": f"{LOCAL_URL}/incidents/response-times"},
    {
        "name": "Generate CSV Report (Post)",
        "method": "POST",
        "url": f"{LOCAL_URL}/reports/generate",
        "body": {
            "report_type": "incident_summary",
            "date_from": "2026-06-01T00:00:00.000Z",
            "date_to": "2026-06-15T00:00:00.000Z"
        }
    }
]

def debug_direct_calls():
    print("==================================================")
    print("   Debugging FastAPI Analytics Services Directly  ")
    print("==================================================")
    
    for ep in ENDPOINTS:
        name = ep["name"]
        url = ep["url"]
        print(f"\nCalling: {name} ({url})...")
        
        try:
            method = ep.get("method", "GET")
            headers = {"Content-Type": "application/json"} if method == "POST" else {}
            req = urllib.request.Request(url, method=method, headers=headers)
            if "body" in ep:
                req.data = json.dumps(ep["body"]).encode("utf-8")
            with urllib.request.urlopen(req) as response:
                print(f"Result: SUCCESS (Status: {response.status})")
                print(f"Body: {response.read().decode('utf-8')}")
        except urllib.error.HTTPError as e:
            print(f"Result: FAILED (Status: {e.code})")
            print(f"Details: {e.read().decode('utf-8')}")
        except Exception as e:
            print(f"Result: ERROR ({str(e)})")

if __name__ == "__main__":
    debug_direct_calls()
