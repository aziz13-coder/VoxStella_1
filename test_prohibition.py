#!/usr/bin/env python3
"""
Test script to trigger prohibition checking with debug output
"""
import json
import urllib.error
import urllib.request


def _post_chart_request(chart_request):
    """POST chart payload using stdlib HTTP so the test stays cross-platform."""
    payload = json.dumps(chart_request).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:5001/api/calculate-chart",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return getattr(resp, "status", 200), body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, body

def test_prohibition():
    print("=== TESTING PROHIBITION DETECTION ===")
    print()
    
    # Run the horary API with the problematic chart
    chart_request = {
        "question": "will I win in the lottery?",
        "location": {
            "city": "ישראל",
            "lat": 30.8124247,
            "lon": 34.8594762
        },
        "asked_at": "2025-09-01T05:14:25.785Z",
        "enhanced": True,
        "window_days": 30
    }
    
    print("Submitting chart request to backend...")
    print("Look for DEBUG messages in the backend log showing Mars prohibition logic:")
    print()
    print("Expected DEBUG output:")
    print("- 'DEBUG: Checking Mars for prohibition...'")
    print("- 'DEBUG: Mars Square: t1(Sun)=..., t2(Jupiter)=4.08'") 
    print("- 'DEBUG: Mars Square: valid1=..., valid2=...'")
    print("- If valid2=True: 'DEBUG: PROHIBITION DETECTED! Mars Square Jupiter in 4.08 days'")
    print("- If valid2=False: Debug message showing why _leg_valid failed")
    print()
    
    try:
        status_code, body = _post_chart_request(chart_request)
        print(f"HTTP status: {status_code}")
        
        print("Backend response:")
        if body:
            response_data = json.loads(body)
            judgment = response_data.get('judgment', 'Unknown')
            confidence = response_data.get('confidence', 'Unknown') 
            print(f"Judgment: {judgment}")
            print(f"Confidence: {confidence}")
            
            if judgment == 'YES':
                print("❌ PROHIBITION NOT DETECTED - Chart should be denied")
            else:
                print("✓ PROHIBITION DETECTED - Chart correctly denied")
        else:
            print("No response received")

    except Exception as e:
        print(f"Error: {e}")
        
    print()
    print("Check the backend log (backend/horary_api.log) for DEBUG messages")
    print("The debug output will show exactly where the Mars prohibition logic fails")

if __name__ == "__main__":
    test_prohibition()
