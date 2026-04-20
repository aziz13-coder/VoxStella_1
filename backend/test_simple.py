#!/usr/bin/env python3
"""Simple test to isolate translation detection issues"""

import sys
import os

# Add path for imports
sys.path.append('.')

def main():
    """Test that should trigger translation detection debug output"""
    
    # Simulate the chart calculation that triggers translation
    import subprocess
    import json
    
    # Make a quick chart request to trigger the debug output
    try:
        result = subprocess.run([
            'curl', '-s', '-X', 'POST', 'http://localhost:5000/api/calculate-chart',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                'question': 'Will my relationship improve?',
                'datetime': '28/02/1970 15:39',
                'location': 'Asia/Jerusalem',
                'timezone': 'Asia/Jerusalem'
            })
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            try:
                chart_data = json.loads(result.stdout)
                print(f"Chart calculated successfully")
                print(f"Result: {chart_data.get('result', 'unknown')} ({chart_data.get('confidence', 0)}%)")
                print(f"Perfection: {chart_data.get('traditional_factors', {}).get('perfection_type', 'none')}")
                
                # Look for translation in various fields
                translation_found = False
                if 'translation' in str(chart_data.get('reasoning', [])).lower():
                    translation_found = True
                if chart_data.get('traditional_factors', {}).get('perfection_type') == 'translation':
                    translation_found = True
                    
                print(f"Translation detected: {translation_found}")
                
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Raw response: {result.stdout[:200]}...")
        else:
            print(f"Curl failed with return code: {result.returncode}")
            print(f"Error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("Request timed out")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()