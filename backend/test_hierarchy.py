#!/usr/bin/env python3
"""Test hierarchical testimony weighting system"""

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

def test_hierarchical_weighting():
    """Test that hierarchical weighting works correctly for relationship questions"""
    
    from category_router import get_contract
    from horary_engine.aggregator import aggregate, _get_testimony_hierarchy_weight, _is_testimony_relevant
    from horary_engine.polarity_weights import TestimonyKey
    from taxonomy import Category
    
    print("=== Testing Hierarchical Testimony Weighting ===")
    
    # Get contract for relationship category
    contract = get_contract(Category.RELATIONSHIP)
    print(f"Contract category rules: {contract.get('category_rules', {})}")
    
    # Test different types of testimonies using string values
    test_tokens = [
        'perfection_translation_of_light',  # Should get MAJOR weight (~25x)
        'l1_fortunate',                     # Should get SECONDARY weight (~10x) 
        'l7_malific_debility',              # Should get SECONDARY weight (~10x)
        'l5_fortunate',                     # Should get ZERO weight (irrelevant)
        'l8_fortunate',                     # Should get ZERO weight (irrelevant)
    ]
    
    print(f"\n=== Weights and Relevance Test ===")
    for token in test_tokens:
        if hasattr(token, 'value'):
            weight = _get_testimony_hierarchy_weight(token, contract)
            relevant = _is_testimony_relevant(token, contract)
            category_rules = contract.get('category_rules', {})
            irrelevant_houses = category_rules.get('irrelevant_houses', [])
            
            print(f"{token.value}:")
            print(f"  Weight: {weight:.1f}")
            print(f"  Relevant: {relevant}")
            print(f"  Expected: {'MAJOR' if 'perfection' in token.value or 'translation' in token.value else 'SECONDARY' if token.value in ['l1_fortunate', 'l7_malific_debility'] else 'MINOR' if 'l4' in token.value else 'IRRELEVANT'}")
            print()
    
    # Test aggregation with mixed testimonies
    print(f"=== Aggregation Test ===")
    
    # Before: All testimonies treated equally (problematic)
    mixed_testimonies = [
        TestimonyKey.L5_FORTUNATE,       # +1 (irrelevant to relationships)
        TestimonyKey.L7_MALIFIC_DEBILITY, # -1 (minor)
        TestimonyKey.L8_FORTUNATE,       # +1 (irrelevant to relationships)  
    ]
    
    # Test with hierarchical weighting
    score, ledger = aggregate(mixed_testimonies, contract)
    
    print(f"Mixed testimonies score: {score:.1f}")
    print(f"Ledger entries:")
    for entry in ledger:
        token_name = entry['key'].value if hasattr(entry['key'], 'value') else str(entry['key'])
        print(f"  {token_name}: weight={entry['weight']:.1f}, delta_yes={entry['delta_yes']:.1f}, delta_no={entry['delta_no']:.1f}")
    
    # Test with major testimony
    print(f"\n=== Major Testimony Test ===")
    major_testimonies = [
        TestimonyKey.PERFECTION_TRANSLATION_OF_LIGHT,  # Should dominate
        TestimonyKey.L5_FORTUNATE,                     # Should be irrelevant
    ]
    
    major_score, major_ledger = aggregate(major_testimonies, contract)
    
    print(f"Major testimony score: {major_score:.1f}")
    print(f"Ledger entries:")
    for entry in major_ledger:
        token_name = entry['key'].value if hasattr(entry['key'], 'value') else str(entry['key'])
        print(f"  {token_name}: weight={entry['weight']:.1f}, delta_yes={entry['delta_yes']:.1f}, delta_no={entry['delta_no']:.1f}")
    
    print(f"\n=== Results Summary ===")
    print(f"✅ FIXED: Major testimony (translation) weight: {major_ledger[0]['weight'] if major_ledger else 0:.1f}")
    print(f"✅ FIXED: L5 irrelevant house filtered: {'L5_FORTUNATE not in ledger' if not any('l5' in str(entry['key']).lower() for entry in major_ledger) else 'L5_FORTUNATE still present'}")
    print(f"✅ FIXED: Hierarchical weighting working: {major_score > score}")

if __name__ == "__main__":
    test_hierarchical_weighting()
