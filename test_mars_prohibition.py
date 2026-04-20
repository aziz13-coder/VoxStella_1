#!/usr/bin/env python3
import json
import time
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

def test_mars_prohibition():
    print("=== TESTING MARS PROHIBITION WITH DEBUG OUTPUT ===")
    print()
    
    # Original problematic chart data
    chart_request = {
        "question": "will I win in the lottery?",
        "location": {
            "city": "israel",
            "lat": 30.8124247,
            "lon": 34.8594762
        },
        "asked_at": "2025-09-01T02:14:00.000Z",  # Original chart time
        "enhanced": True,
        "window_days": 30
    }
    
    print("Testing original chart with Mars-Jupiter prohibition...")
    print("Expected: Mars Square Jupiter in 4.08 days should prohibit Sun-Jupiter sextile")
    print()
    print("Looking for debug output in backend log:")
    print("- '=== PROHIBITION CHECK DEBUG ==='")
    print("- 'Mars Square: t1(Sun)=..., t2(Jupiter)=4.08'")  
    print("- 'Mars Square validation: valid1=..., valid2=...'")
    print("- If valid2=True: '*** PROHIBITION DETECTED: Mars Square Jupiter in 4.08 days ***'")
    print()
    
    try:
        # Give server time to reload
        time.sleep(2)

        status_code, body = _post_chart_request(chart_request)
        print(f"HTTP status: {status_code}")

        if body:
            response_data = json.loads(body)
            judgment = response_data.get('judgment', 'Unknown')
            confidence = response_data.get('confidence', 'Unknown') 
            perfection_type = response_data.get('traditional_factors', {}).get('perfection_type', 'Unknown')
            
            print(f"Result:")
            print(f"  Judgment: {judgment}")
            print(f"  Confidence: {confidence}")
            print(f"  Perfection Type: {perfection_type}")
            print()
            
            if judgment == 'YES':
                print("❌ PROHIBITION STILL NOT DETECTED")
                print("Check backend log for debug messages to see where the logic fails")
            else:
                print("✓ PROHIBITION DETECTED - Mars blocking Sun-Jupiter")
                
        else:
            print("No response received")
            
    except Exception as e:
        print(f"Error: {e}")
        
    print()
    print("Check backend/horary_api.log for detailed debug output")
    print("The debug messages will show exactly what happens in the prohibition logic")

if __name__ == "__main__":
    test_mars_prohibition()
