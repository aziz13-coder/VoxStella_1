#!/usr/bin/env python3

import json
import requests
import sys

def test_api_reception_field():
    print("=== Testing Real API Reception Field ===\n")
    
    # Make a test request to the actual API
    url = "http://127.0.0.1:52525/api/calculate-chart"
    
    test_data = {
        "location": "New York, NY",
        "date": "2023-12-15",
        "time": "14:30:00",
        "question": "Will I get the job?"
    }
    
    try:
        print("Making API request...")
        response = requests.post(url, json=test_data, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check traditional_factors structure
            trad_factors = data.get('traditional_factors', {})
            print(f"Traditional factors keys: {list(trad_factors.keys())}")
            
            if 'reception' in trad_factors:
                reception = trad_factors['reception']
                print(f"\nReception field found:")
                print(f"  Type: {type(reception)}")
                print(f"  Value: {reception}")
                print(f"  Repr: {repr(reception)}")
                print(f"  Has .replace(): {hasattr(reception, 'replace') if reception else 'N/A (None)'}")
                
                # Try calling .replace() to see if it works
                if reception is not None:
                    try:
                        test_replace = reception.replace('test', 'test')
                        print(f"  .replace() test: SUCCESS")
                    except Exception as e:
                        print(f"  .replace() test: FAILED - {e}")
            else:
                print("\nNo 'reception' field found in traditional_factors")
                
            # Print the entire traditional_factors for inspection
            print(f"\nComplete traditional_factors structure:")
            print(json.dumps(trad_factors, indent=2))
            
        else:
            print(f"API request failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api_reception_field()