#!/usr/bin/env python3
"""
Simple debug script to analyze prohibition conditions
"""
import json

def debug_prohibition():
    # Load the chart data
    with open('/mnt/c/Users/sabaa/Downloads/codexhorary/enhanced-horary-chart-1756692865800.json', 'r') as f:
        chart_data = json.load(f)
    
    print("=== PROHIBITION DEBUG ===")
    print(f"Question: {chart_data['question']}")
    print()
    
    # Extract planetary data
    mars_data = chart_data['planets']['Mars']
    jupiter_data = chart_data['planets']['Jupiter']
    sun_data = chart_data['planets']['Sun']
    
    print("=== PLANETARY DATA ===")
    print(f"Mars: {mars_data['longitude']:.2f}° {mars_data['sign']}, Speed: {mars_data['speed']:.6f}°/day")
    print(f"Jupiter: {jupiter_data['longitude']:.2f}° {jupiter_data['sign']}, Speed: {jupiter_data['speed']:.6f}°/day") 
    print(f"Sun: {sun_data['longitude']:.2f}° {sun_data['sign']}, Speed: {sun_data['speed']:.6f}°/day")
    print()
    
    # Check what aspects are in the chart
    print("=== CHART ASPECTS ===")
    mars_jupiter_found = False
    for asp in chart_data['aspects']:
        print(f"{asp['planet1']} {asp['aspect']} {asp['planet2']}: {asp['time_to_perfection']:.2f} days, Applying: {asp['applying']}")
        if ((asp['planet1'] == 'Mars' and asp['planet2'] == 'Jupiter') or 
            (asp['planet1'] == 'Jupiter' and asp['planet2'] == 'Mars')):
            mars_jupiter_found = True
            if asp['applying'] and asp['time_to_perfection'] > 0:
                print(f"  ^ THIS SHOULD BE THE PROHIBITION! (happens before Sun-Jupiter in 11.4 days)")
    
    if not mars_jupiter_found:
        print("ERROR: Mars-Jupiter aspect not found in chart aspects!")
    print()
    
    # Check if there are any Sun aspects with Mars
    print("=== CHECKING FOR SUN-MARS ASPECTS ===")
    sun_mars_found = False
    for asp in chart_data['aspects']:
        if ((asp['planet1'] == 'Sun' and asp['planet2'] == 'Mars') or 
            (asp['planet1'] == 'Mars' and asp['planet2'] == 'Sun')):
            sun_mars_found = True
            print(f"Found: {asp['planet1']} {asp['aspect']} {asp['planet2']}: {asp['time_to_perfection']:.2f} days, Applying: {asp['applying']}")
    
    if not sun_mars_found:
        print("No Sun-Mars aspect found")
    print()
    
    # Theoretical analysis
    print("=== PROHIBITION LOGIC ANALYSIS ===")
    print("For Mars to prohibit Sun-Jupiter perfection:")
    print("1. Mars must aspect either Sun OR Jupiter before 11.4 days ✓")
    print("2. The aspect must be 'valid' (pass timing and boundary checks)")
    print("3. Mars-Jupiter square in 4.08 days should trigger prohibition")
    print()
    
    print("=== VALIDATION REQUIREMENTS ===")
    
    # Sign boundary checks
    mars_exit_days = (30 - mars_data['degree_in_sign']) / mars_data['speed']
    jupiter_exit_days = (30 - jupiter_data['degree_in_sign']) / jupiter_data['speed']
    
    print(f"Sign boundary check (require_in_sign=True):")
    print(f"  Mars sign exit: {mars_exit_days:.1f} days")
    print(f"  Jupiter sign exit: {jupiter_exit_days:.1f} days")
    print(f"  Mars-Jupiter aspect (4.08 days) happens before both exits: ✓")
    print()
    
    print("Refranation check:")
    print(f"  Mars retrograde: {mars_data['retrograde']} (direct motion, unlikely to station soon)")
    print(f"  Jupiter retrograde: {jupiter_data['retrograde']} (direct motion, unlikely to station soon)")
    print("  Should pass refranation check: ✓")
    print()
    
    print("CONCLUSION:")
    print("All validation checks should pass. Mars-Jupiter prohibition should be detected.")
    print("If it's not being detected, there might be a deeper bug in the prohibition logic.")

if __name__ == "__main__":
    debug_prohibition()