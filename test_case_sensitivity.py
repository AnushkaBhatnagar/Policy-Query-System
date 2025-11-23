#!/usr/bin/env python3
"""Test case-sensitivity fixes in policy_server"""

import sys
from pathlib import Path

# Add policy_server to path
sys.path.insert(0, str(Path(__file__).parent / "policy_server"))

from server import PolicySearch, load_documents, DOCUMENTS, CONFLICTS, RULE_INDEX

# Load documents
load_documents()

# Create search engine
search = PolicySearch(DOCUMENTS, CONFLICTS)

print("="*60)
print("CASE-SENSITIVITY TEST")
print("="*60)

# Test 1: get_rule with different cases
print("\n1. Testing get_rule() with different cases:")
print("-" * 60)

test_ids = [
    "PhD_SEAS:ALGO-PREREQ-001",  # Exact case
    "phd_seas:algo-prereq-001",  # All lowercase
    "PHD_SEAS:ALGO-PREREQ-001",  # All uppercase
    "Phd_Seas:Algo-Prereq-001",  # Mixed case
]

for test_id in test_ids:
    result = search.get_rule(test_id)
    if result:
        print(f"✓ '{test_id}' → Found: {result['id']}")
    else:
        print(f"✗ '{test_id}' → NOT FOUND")

# Test 2: search with department filter
print("\n2. Testing search() with department filter (different cases):")
print("-" * 60)

dept_tests = [
    ("algorithm", "PhD_SEAS"),
    ("algorithm", "phd_seas"),
    ("algorithm", "PHD_SEAS"),
]

for query, dept in dept_tests:
    results = search.search(query, department=dept, max_results=3)
    print(f"Query: '{query}' | Dept: '{dept}' → {len(results)} results")
    if results:
        print(f"  Top: {results[0]['rule_id']}")

# Test 3: check_conflicts with different cases
print("\n3. Testing check_conflicts() with different cases:")
print("-" * 60)

# Get a sample rule ID
sample_rule = list(RULE_INDEX.keys())[0]
print(f"Sample rule: {sample_rule}")

conflict_tests = [
    [sample_rule],  # Exact case
    [sample_rule.lower()],  # Lowercase
    [sample_rule.upper()],  # Uppercase
]

for test_ids in conflict_tests:
    conflicts = search.check_conflicts(test_ids)
    print(f"Check: {test_ids[0][:30]}... → {len(conflicts)} conflicts")

print("\n" + "="*60)
print("✓ All case-sensitivity tests completed!")
