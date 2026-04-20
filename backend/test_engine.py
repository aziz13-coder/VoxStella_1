#!/usr/bin/env python3
"""Simple test to verify translation detection is working"""

import json
import sys
import os

def main():
    """Test the specific chart that should show Moon translation"""
    
    # Read the chart JSON directly
    chart_file = "/mnt/c/Users/sabaa/Downloads/codexhorary/enhanced-horary-chart-1756462186560.json"
    
    try:
        with open(chart_file, 'r') as f:
            chart_data = json.load(f)
    except FileNotFoundError:
        print("Chart file not found")
        return
        
    print("=== Chart Analysis ===")
    print(f"Question: {chart_data['question']}")
    print(f"Category: {chart_data['category']}")
    
    # Extract key data
    moon = chart_data['planets']['Moon']
    sun = chart_data['planets']['Sun'] 
    saturn = chart_data['planets']['Saturn']
    
    print(f"\nPlanet Positions:")
    print(f"  Moon: {moon['longitude']:.1f}° (speed {moon['speed']:.2f}°/day) in {moon['sign']}")
    print(f"  Sun: {sun['longitude']:.1f}° (speed {sun['speed']:.2f}°/day) in {sun['sign']} [L1]")
    print(f"  Saturn: {saturn['longitude']:.1f}° (speed {saturn['speed']:.2f}°/day) in {saturn['sign']} [L7]")
    
    # Check existing aspects
    print(f"\nExisting Aspects:")
    moon_aspects = [a for a in chart_data['aspects'] if 'Moon' in [a['planet1'], a['planet2']]]
    if moon_aspects:
        for aspect in moon_aspects:
            other_planet = aspect['planet2'] if aspect['planet1'] == 'Moon' else aspect['planet1']
            status = "APPLYING" if aspect['applying'] else "SEPARATING"
            print(f"  Moon {aspect['aspect']} {other_planet}: {status} ({aspect['orb']:.1f}° orb)")
    else:
        print("  No Moon aspects in chart.aspects")
    
    # Check reasoning
    print(f"\nReasoning Tokens:")
    for reason in chart_data['reasoning']:
        polarity = "+" if reason['polarity'] == 'POSITIVE' else "-"
        print(f"  {polarity}{reason['weight']} {reason['key']} ({reason['family']})")
    
    # Check if translation was detected
    reasoning_text = str(chart_data.get('reasoning', []))
    ledger_text = str(chart_data.get('ledger', []))
    
    translation_found = any('translation' in str(item).lower() for item in [reasoning_text, ledger_text])
    perfection_type = chart_data.get('traditional_factors', {}).get('perfection_type', 'none')
    
    print(f"\nResult:")
    print(f"  Verdict: {chart_data.get('result', 'unknown')} ({chart_data.get('confidence', 0)}% confidence)")
    print(f"  Perfection Type: {perfection_type}")
    print(f"  Translation Detected: {translation_found}")
    
    if perfection_type == 'none' and not translation_found:
        print(f"\n❌ PROBLEM: No translation detected despite valid Moon sequence")
        print(f"   Expected: Moon translation between L7 (Saturn) and L1 (Sun)")
        print(f"   - Moon opposition Saturn ~2 days ago (separating)")
        print(f"   - Moon sextile Sun in ~2.5 days (applying, cross-sign)")
    else:
        print(f"\n✅ Translation detection working correctly")

if __name__ == "__main__":
    main()