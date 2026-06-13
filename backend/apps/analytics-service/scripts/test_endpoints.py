import urllib.request
import urllib.error
import json

# Configuration
GATEWAY_URL = "http://localhost:3000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MDA2MzVjZC00ZDU2LTRlMjAtOTE3Mi02MmI1OWEwMzMwNDMiLCJlbWFpbCI6ImFkbWluQHNlbnRpbmVsLmNvbSIsInJvbGUiOiJhZG1pbiIsImlhdCI6MTc4MTMzODgwMywiZXhwIjoxNzgxMzM5NzAzfQ.IGO22JnCqf0Tr9flWYepRREhaJRB67HM55sTq0KQ1RE"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

ENDPOINTS = [
    {
        "name": "Dashboard Summary",
        "method": "GET",
        "url": f"{GATEWAY_URL}/api/v1/analytics/dashboard/"
    },
    {
        "name": "Incident Stats",
        "method": "GET",
        "url": f"{GATEWAY_URL}/api/v1/analytics/incidents/stats"
    },
    {
        "name": "Incident Trends",
        "method": "GET",
        "url": f"{GATEWAY_URL}/api/v1/analytics/incidents/trends"
    },
    {
        "name": "Response Times Stats",
        "method": "GET",
        "url": f"{GATEWAY_URL}/api/v1/analytics/incidents/response-times"
    },
    {
        "name": "Camera Performance",
        "method": "GET",
        "url": f"{GATEWAY_URL}/api/v1/analytics/cameras/performance"
    },
    {
        "name": "Spatial Heatmap",
        "method": "GET",
        "url": f"{GATEWAY_URL}/api/v1/analytics/heatmap/"
    },
    {
        "name": "Generate CSV Report (Post)",
        "method": "POST",
        "url": f"{GATEWAY_URL}/api/v1/analytics/reports/generate",
        "body": {
            "report_type": "incident_summary",
            "date_from": "2026-06-01T00:00:00.000Z",
            "date_to": "2026-06-15T00:00:00.000Z"
        }
    }
]

def run_tests():
    print("==================================================")
    print("      Omnisight Analytics Endpoints Test         ")
    print("==================================================")
    
    success_count = 0
    
    for endpoint in ENDPOINTS:
        name = endpoint["name"]
        method = endpoint["method"]
        url = endpoint["url"]
        
        print(f"\n[Test] {name}...")
        print(f"       {method} {url}")
        
        req = urllib.request.Request(url, headers=HEADERS, method=method)
        
        if "body" in endpoint:
            data = json.dumps(endpoint["body"]).encode("utf-8")
            req.data = data
            
        try:
            with urllib.request.urlopen(req) as response:
                status = response.status
                body = response.read()
                
                print(f"       Result: SUCCESS (Status Code: {status})")
                
                # Try printing a brief snippet of the response JSON or content length
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    res_json = json.loads(body.decode("utf-8"))
                    # If NestJS responds with standard payload wrapper
                    data_part = res_json.get("data") if isinstance(res_json, dict) and "data" in res_json else res_json
                    snippet = str(data_part)[:150] + "..." if len(str(data_part)) > 150 else str(data_part)
                    print(f"       Response Snippet: {snippet}")
                else:
                    print(f"       Response: File/Binary ({len(body)} bytes)")
                
                success_count += 1
                
        except urllib.error.HTTPError as e:
            print(f"       Result: FAILED (Status Code: {e.code})")
            try:
                error_body = e.read().decode("utf-8")
                print(f"       Error Detail: {error_body}")
            except Exception:
                pass
        except urllib.error.URLError as e:
            print(f"       Result: FAILED (Cannot reach server: {e.reason})")
            
    print("\n==================================================")
    print(f" Test Run Completed: {success_count}/{len(ENDPOINTS)} Passed")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
