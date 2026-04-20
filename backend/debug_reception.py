#!/usr/bin/env python3

import json
import sys
import os

# Add the current directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import make_json_safe
from horary_engine.engine import HoraryEngine
from horary_engine.reception import TraditionalReceptionCalculator

def test_reception_serialization():
    print("=== Testing Reception Field Serialization ===\n")
    
    # Create a test sample data structure similar to what the engine returns
    sample_chart_data = {
        "traditional_factors": {
            "perfection_type": "direct",
            "reception": "mutual_rulership",  # This should remain a string
            "querent_strength": 3,
            "quesited_strength": 2
        },
        "result": "YES",
        "confidence": 75
    }
    
    print("Original data:")
    print(f"  Type of reception: {type(sample_chart_data['traditional_factors']['reception'])}")
    print(f"  Value of reception: {sample_chart_data['traditional_factors']['reception']}")
    print(f"  Can call .replace(): {hasattr(sample_chart_data['traditional_factors']['reception'], 'replace')}")
    
    # Test JSON serialization with make_json_safe
    json_safe_data = make_json_safe(sample_chart_data)
    
    print("\nAfter make_json_safe:")
    print(f"  Type of reception: {type(json_safe_data['traditional_factors']['reception'])}")
    print(f"  Value of reception: {json_safe_data['traditional_factors']['reception']}")
    print(f"  Can call .replace(): {hasattr(json_safe_data['traditional_factors']['reception'], 'replace')}")
    
    # Test actual JSON serialization
    json_string = json.dumps(json_safe_data)
    parsed_back = json.loads(json_string)
    
    print("\nAfter full JSON serialization cycle:")
    print(f"  Type of reception: {type(parsed_back['traditional_factors']['reception'])}")
    print(f"  Value of reception: {parsed_back['traditional_factors']['reception']}")
    print(f"  Can call .replace(): {hasattr(parsed_back['traditional_factors']['reception'], 'replace')}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_reception_serialization()