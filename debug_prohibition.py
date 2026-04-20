#!/usr/bin/env python3
"""
Debug script to trace prohibition detection for the lottery chart
"""
import sys
import os
import json

# Add backend to path
sys.path.insert(0, '/mnt/c/Users/sabaa/Downloads/codexhorary/backend')

from models import Planet, Aspect, PlanetPosition, HoraryChart
from horary_engine.perfection import check_future_prohibitions, CLASSICAL_PLANETS, ASPECT_TYPES
from datetime import datetime
import swisseph as swe

def debug_prohibition_check():
    # Load the chart data
    with open('/mnt/c/Users/sabaa/Downloads/codexhorary/enhanced-horary-chart-1756692865800.json', 'r') as f:
        chart_data = json.load(f)
    
    print("=== PROHIBITION DEBUG ===")
    print(f"Question: {chart_data['question']}")
    print(f"Significators: Sun (querent) -> Jupiter (quesited)")
    print(f"Planned perfection: Sun-Jupiter sextile in 11.4 days")
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
    
    # Check aspect calculation
    mars_lon = mars_data['longitude']
    jupiter_lon = jupiter_data['longitude']
    mars_speed = mars_data['speed']
    jupiter_speed = jupiter_data['speed']
    
    # Calculate square aspect timing manually
    current_separation = abs(mars_lon - jupiter_lon)
    if current_separation > 180:
        current_separation = 360 - current_separation
    
    target_separation = 90  # Square
    orb = abs(current_separation - target_separation)
    relative_speed = abs(mars_speed - jupiter_speed)
    
    print("=== ASPECT CALCULATION ===")
    print(f"Current angular separation: {current_separation:.2f}°")
    print(f"Target separation (square): {target_separation}°")
    print(f"Orb: {orb:.2f}°")
    print(f"Relative speed: {relative_speed:.6f}°/day")
    print(f"Time to exact: {orb / relative_speed:.2f} days")
    print()
    
    # Check what's in the chart aspects
    print("=== CHART ASPECTS ===")
    for asp in chart_data['aspects']:
        print(f"{asp['planet1']} {asp['aspect']} {asp['planet2']}: {asp['time_to_perfection']:.2f} days, Applying: {asp['applying']}")
    print()
    
    # Check CLASSICAL_PLANETS and ASPECT_TYPES
    print("=== PROHIBITION CHECKER SCOPE ===")
    print(f"CLASSICAL_PLANETS: {[p.value for p in CLASSICAL_PLANETS]}")
    print(f"ASPECT_TYPES: {[a.value for a in ASPECT_TYPES]}")
    print()
    print(f"Mars in CLASSICAL_PLANETS: {'Mars' in [p.value for p in CLASSICAL_PLANETS]}")
    print(f"Square in ASPECT_TYPES: {'Square' in [a.value for a in ASPECT_TYPES]}")
    print()
    
    # Check why Mars-Jupiter prohibition might be filtered
    print("=== POTENTIAL FILTERING CONDITIONS ===")
    print("1. Sign boundary check:")
    
    # Mars sign boundary
    mars_degree_in_sign = mars_data['degree_in_sign'] 
    degrees_to_mars_exit = 30 - mars_degree_in_sign
    days_to_mars_exit = degrees_to_mars_exit / mars_speed
    print(f"   Mars: {degrees_to_mars_exit:.2f}° to sign exit, {days_to_mars_exit:.1f} days")
    
    # Jupiter sign boundary  
    jupiter_degree_in_sign = jupiter_data['degree_in_sign']
    degrees_to_jupiter_exit = 30 - jupiter_degree_in_sign
    days_to_jupiter_exit = degrees_to_jupiter_exit / jupiter_speed
    print(f"   Jupiter: {degrees_to_jupiter_exit:.2f}° to sign exit, {days_to_jupiter_exit:.1f} days")
    
    aspect_timing = 4.08
    print(f"   Aspect timing ({aspect_timing} days) < Mars exit ({days_to_mars_exit:.1f} days): {aspect_timing < days_to_mars_exit}")
    print(f"   Aspect timing ({aspect_timing} days) < Jupiter exit ({days_to_jupiter_exit:.1f} days): {aspect_timing < days_to_jupiter_exit}")
    print()
    
    print("2. Refranation check:")
    print(f"   Mars: Direct motion (speed {mars_speed:.3f}°/day), unlikely to station soon")
    print(f"   Jupiter: Direct motion (speed {jupiter_speed:.3f}°/day), unlikely to station soon")
    print()
    
    print("3. Timing window:")
    print(f"   days_ahead parameter should be 11.4 days (Sun-Jupiter perfection)")
    print(f"   Mars-Jupiter timing (4.08) < window (11.4): {4.08 < 11.4}")

if __name__ == "__main__":
    debug_prohibition_check()