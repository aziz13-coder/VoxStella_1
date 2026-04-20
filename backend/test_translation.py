#!/usr/bin/env python3
"""Test the enhanced lunar translation detection logic"""

# Simple test of the lunar sequence calculation without full engine imports
def signed_longitude_delta(lon1, lon2):
    """Return signed longitudinal difference lon1-lon2 normalised to [-180, 180]."""
    return (lon1 - lon2 + 180) % 360 - 180

def time_to_perfection(planet1_lon, planet1_speed, planet2_lon, planet2_speed, aspect_degrees):
    """Calculate time to aspect perfection"""
    delta = ((planet1_lon - planet2_lon - aspect_degrees + 180) % 360) - 180
    v = planet1_speed - planet2_speed
    if v == 0:
        return float('inf')
    return -delta / v

def test_recent_separations():
    """Test the time-based separating aspect detection"""
    print("=== Testing Time-Based Recent Separations ===")
    
    # Chart data
    moon_lon = 242.8    # Sagittarius
    moon_speed = 13.46
    sun_lon = 339.6     # Pisces (L1) 
    sun_speed = 1.00
    saturn_lon = 34.8   # Taurus (L7)
    saturn_speed = 0.09
    
    def time_to_perfection(planet1_lon, planet1_speed, planet2_lon, planet2_speed, aspect_degrees):
        """Calculate time to aspect perfection"""
        delta = ((planet1_lon - planet2_lon - aspect_degrees + 180) % 360) - 180
        v = planet1_speed - planet2_speed
        if v == 0:
            return float('inf')
        return -delta / v
    
    print(f"Moon: {moon_lon}° (speed {moon_speed}°/day)")
    print(f"Sun: {sun_lon}° (L1, speed {sun_speed}°/day)")
    print(f"Saturn: {saturn_lon}° (L7, speed {saturn_speed}°/day)")
    
    # Aspect degrees for traditional aspects
    aspects = {
        'CONJUNCTION': 0,
        'SEXTILE': 60, 
        'SQUARE': 90,
        'TRINE': 120,
        'OPPOSITION': 180
    }
    
    print(f"\n=== TIME-BASED Separating Aspects Detection ===")
    separating_found = []
    
    for target_name, target_lon, target_speed in [('Sun', sun_lon, sun_speed), ('Saturn', saturn_lon, saturn_speed)]:
        print(f"\nMoon-{target_name} time analysis:")
        best_separating = None
        most_recent_time = float('inf')
        
        for aspect_name, aspect_degrees in aspects.items():
            t = time_to_perfection(moon_lon, moon_speed, target_lon, target_speed, aspect_degrees)
            
            if t < 0 and abs(t) <= 7:  # Separated within last 7 days
                time_since_exact = abs(t)
                degrees_traveled = time_since_exact * moon_speed
                
                print(f"  {aspect_name}: {t:.2f} days ago (traveled {degrees_traveled:.1f}° since)")
                
                # Keep most recent
                if time_since_exact < most_recent_time:
                    most_recent_time = time_since_exact
                    best_separating = {
                        'target': target_name,
                        'aspect': aspect_name,
                        'time_ago': time_since_exact,
                        'degrees_traveled': degrees_traveled
                    }
        
        if best_separating:
            separating_found.append(best_separating)
            print(f"  → Best recent separation: {best_separating['aspect']} ({best_separating['time_ago']:.1f} days ago)")
    
    assert separating_found, "Expected at least one recent separating lunar aspect"

def test_translation_sequence():
    """Test both separating and applying aspects for translation"""
    print("=== Testing Complete Translation Sequence ===")
    
    # First test recent separations with pure time-based analysis
    test_recent_separations()
    
    # Chart data
    moon_lon = 242.8    # Sagittarius
    moon_speed = 13.46
    sun_lon = 339.6     # Pisces (L1) 
    sun_speed = 1.00
    saturn_lon = 34.8   # Taurus (L7)
    saturn_speed = 0.09
    
    print(f"\nMoon: {moon_lon}° (speed {moon_speed}°/day)")
    print(f"Sun: {sun_lon}° (L1, speed {sun_speed}°/day)")
    print(f"Saturn: {saturn_lon}° (L7, speed {saturn_speed}°/day)")
    
    # Aspect degrees for traditional aspects
    aspects = {
        'CONJUNCTION': 0,
        'SEXTILE': 60, 
        'SQUARE': 90,
        'TRINE': 120,
        'OPPOSITION': 180
    }
    
    print(f"\n=== Recent Separating Aspects (last 7 days) ===")
    separating_aspects = []
    
    for target_name, target_lon, target_speed in [('Sun', sun_lon, sun_speed), ('Saturn', saturn_lon, saturn_speed)]:
        print(f"\nMoon-{target_name} aspects:")
        for aspect_name, aspect_degrees in aspects.items():
            t = time_to_perfection(moon_lon, moon_speed, target_lon, target_speed, aspect_degrees)
            if t < 0 and abs(t) <= 7:  # Separating and within 7 days
                separating_aspects.append({
                    'target': target_name,
                    'aspect': aspect_name,
                    'time_ago': abs(t),
                    'applying': False
                })
                print(f"  {aspect_name}: {t:.2f} days (SEPARATING)")
    
    print(f"\n=== Future Applying Aspects (next 15 days, cross-sign only) ===")
    applying_aspects = []
    
    current_moon_sign = int(moon_lon // 30)
    
    for days_ahead in [d * 0.5 for d in range(1, 31)]:  # Every 0.5 days up to 15 days
        future_moon_lon = (moon_lon + moon_speed * days_ahead) % 360
        future_moon_sign = int(future_moon_lon // 30)
        
        # Only check cross-sign aspects
        if future_moon_sign != current_moon_sign:
            for target_name, target_lon, target_speed in [('Sun', sun_lon, sun_speed), ('Saturn', saturn_lon, saturn_speed)]:
                future_target_lon = (target_lon + target_speed * days_ahead) % 360
                separation = abs(signed_longitude_delta(future_moon_lon, future_target_lon))
                
                for aspect_name, aspect_degrees in aspects.items():
                    orb_diff = abs(separation - aspect_degrees)
                    max_orb = 8 if aspect_name in ['CONJUNCTION', 'OPPOSITION'] else 6
                    
                    if orb_diff <= max_orb:
                        # Check if this is the first cross-sign aspect found for this target
                        existing = [a for a in applying_aspects if a['target'] == target_name]
                        if not existing or days_ahead < min(a['days_ahead'] for a in existing):
                            # Remove any existing aspects for this target
                            applying_aspects = [a for a in applying_aspects if a['target'] != target_name]
                            
                            applying_aspects.append({
                                'target': target_name,
                                'aspect': aspect_name,
                                'days_ahead': days_ahead,
                                'orb': orb_diff,
                                'applying': True
                            })
                            
                            sign_names = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                                        'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
                            
                            print(f"Day {days_ahead:4.1f}: Moon {aspect_name} {target_name}")
                            print(f"          Moon at {future_moon_lon:5.1f}° ({sign_names[future_moon_sign]})")
                            print(f"          Orb: {orb_diff:.1f}°")
    
    print(f"\n=== Translation Analysis ===")
    print(f"Separating aspects found: {len(separating_aspects)}")
    for aspect in separating_aspects:
        print(f"  Moon {aspect['aspect']} {aspect['target']} ({aspect['time_ago']:.1f} days ago)")
    
    print(f"\nApplying aspects found: {len(applying_aspects)}")
    for aspect in applying_aspects:
        print(f"  Moon {aspect['aspect']} {aspect['target']} (in {aspect['days_ahead']:.1f} days)")
    
    # Check for valid translation patterns (cross-planet sequences)
    valid_translations = []
    
    for sep in separating_aspects:
        for app in applying_aspects:
            if sep['target'] != app['target']:  # Must be different planets
                valid_translations.append({
                    'separating': sep,
                    'applying': app,
                    'total_time': sep['time_ago'] + app['days_ahead'],
                    'sequence': f"Moon separated from {sep['aspect']} {sep['target']} {sep['time_ago']:.1f} days ago, will {app['aspect']} {app['target']} in {app['days_ahead']:.1f} days"
                })
    
    if valid_translations:
        print(f"\n✅ TRANSLATION DETECTED:")
        # Sort by total time span (shorter sequences are more traditional)
        valid_translations.sort(key=lambda x: x['total_time'])
        best = valid_translations[0]
        
        print(f"   Best sequence: {best['sequence']}")
        print(f"   → Classic Translation: Moon connects {best['separating']['target']} to {best['applying']['target']}")
        print(f"   → Total time span: {best['total_time']:.1f} days")
        
        if len(valid_translations) > 1:
            print(f"\n   Alternative sequences:")
            for alt in valid_translations[1:]:
                print(f"     {alt['sequence']}")
    else:
        print(f"\n❌ NO TRANSLATION: No cross-planet separating→applying sequences found")
        if separating_aspects and applying_aspects:
            print(f"   Note: Found separating and applying aspects, but all to same planets (not translation)")

def test_future_lunar_sequence():
    print("=== Testing Future Lunar Translation Sequence ===")
    
    # Chart data
    moon_lon = 242.8    # Sagittarius
    moon_speed = 13.46
    sun_lon = 339.6     # Pisces (L1) 
    saturn_lon = 34.8   # Taurus (L7)
    
    print(f"Moon: {moon_lon}° (speed {moon_speed}°/day)")
    print(f"Sun: {sun_lon}° (L1)")
    print(f"Saturn: {saturn_lon}° (L7)")
    
    # Aspect degrees for traditional aspects
    aspects = {
        'CONJUNCTION': 0,
        'SEXTILE': 60, 
        'SQUARE': 90,
        'TRINE': 120,
        'OPPOSITION': 180
    }
    
    results = []
    
    # Check for future cross-sign aspects
    print("\n=== Scanning future 15 days ===")
    for days_ahead in [d * 0.5 for d in range(1, 31)]:  # Every 0.5 days up to 15 days
        future_moon_lon = (moon_lon + moon_speed * days_ahead) % 360
        current_sign = int(moon_lon // 30)
        future_sign = int(future_moon_lon // 30)
        
        # Only check cross-sign aspects
        if future_sign != current_sign:
            # Check aspects to both significators
            for target_name, target_lon in [('Sun', sun_lon), ('Saturn', saturn_lon)]:
                separation = abs(signed_longitude_delta(future_moon_lon, target_lon))
                
                for aspect_name, aspect_degrees in aspects.items():
                    orb_diff = abs(separation - aspect_degrees)
                    max_orb = 8 if aspect_name in ['CONJUNCTION', 'OPPOSITION'] else 6  # Wider orbs
                    
                    if orb_diff <= max_orb:
                        results.append({
                            'days': days_ahead,
                            'moon_pos': future_moon_lon,
                            'moon_sign': future_sign,
                            'target': target_name,
                            'aspect': aspect_name,
                            'orb': orb_diff,
                            'exact_separation': separation
                        })
                        
                        sign_names = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                                    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
                        
                        print(f"Day {days_ahead:4.1f}: Moon {aspect_name} {target_name}")
                        print(f"          Moon at {future_moon_lon:5.1f}° ({sign_names[future_sign]})")
                        print(f"          Orb: {orb_diff:.1f}°, Separation: {separation:.1f}°")
    
    # Analyze sequence
    print(f"\n=== Translation Sequence Analysis ===")
    if len(results) >= 2:
        # Sort by time
        results.sort(key=lambda x: x['days'])
        print("Detected sequence:")
        for i, result in enumerate(results[:4]):  # First 4 aspects
            print(f"  {i+1}. Day {result['days']:4.1f}: {result['aspect']} {result['target']} (orb {result['orb']:.1f}°)")
        
        # Check for translation pattern
        saturn_aspects = [r for r in results if r['target'] == 'Saturn']
        sun_aspects = [r for r in results if r['target'] == 'Sun']
        
        if saturn_aspects and sun_aspects:
            first_saturn = min(saturn_aspects, key=lambda x: x['days'])
            first_sun = min(sun_aspects, key=lambda x: x['days'])
            
            print(f"\nTranslation Pattern:")
            if first_saturn['days'] < first_sun['days']:
                print(f"  ✓ Moon {first_saturn['aspect']} Saturn (day {first_saturn['days']:.1f})")
                print(f"  ✓ Moon {first_sun['aspect']} Sun (day {first_sun['days']:.1f})")
                print(f"  → Classic Translation: Moon connects L7 to L1")
            else:
                print(f"  ✓ Moon {first_sun['aspect']} Sun (day {first_sun['days']:.1f})")
                print(f"  ✓ Moon {first_saturn['aspect']} Saturn (day {first_saturn['days']:.1f})")
                print(f"  → Reverse Translation: Moon connects L1 to L7")
    else:
        print("No clear translation sequence detected")

if __name__ == "__main__":
    test_translation_sequence()
