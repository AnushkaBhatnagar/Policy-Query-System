#!/usr/bin/env python3
"""Test script to debug policy search"""

import re
import sys
sys.path.append('policy_server')

from server import PolicySearch, load_documents, DOCUMENTS, RULE_INDEX

# Load documents
load_documents()

print("=" * 60)
print("DOCUMENT LOADING TEST")
print("=" * 60)
print(f"Documents loaded: {list(DOCUMENTS.keys())}")
print(f"Total rules indexed: {len(RULE_INDEX)}")

if len(RULE_INDEX) == 0:
    print("\n⚠️  NO RULES INDEXED! Debugging...")
    
    # Test the regex pattern
    content = DOCUMENTS.get('PHD_SEAS', '')
    pattern = r'\[RULE:([^\]]+)\](.*?)(?=\[RULE:|$)'
    
    print(f"\nDocument length: {len(content)} chars")
    print(f"Sample content: {content[:300]}")
    
    matches = list(re.finditer(pattern, content, re.DOTALL))
    print(f"\nRegex pattern found: {len(matches)} matches")
    
    if matches:
        print("\nFirst match details:")
        m = matches[0]
        print(f"  Rule ID: {m.group(1)}")
        print(f"  Content length: {len(m.group(2))}")
        print(f"  Content preview: {m.group(2)[:200]}")
    else:
        print("\n❌ Regex pattern not matching!")
        # Try to find what's wrong
        print("\nSearching for RULE tags manually:")
        rule_tags = re.findall(r'\[RULE:[^\]]+\]', content)
        print(f"Found {len(rule_tags)} RULE tags")
        if rule_tags:
            print(f"First tag: {rule_tags[0]}")
            # Find what comes after first tag
            idx = content.find(rule_tags[0])
            print(f"Content after first tag: {content[idx:idx+500]}")

print("\n" + "=" * 60)
print("SEARCH TEST - 'algorithms prerequisite'")
print("=" * 60)

search = PolicySearch(DOCUMENTS, {})
results = search.search("algorithms prerequisite", max_results=5)

print(f"\nFound {len(results)} results")
for i, result in enumerate(results, 1):
    print(f"\n{i}. {result['rule_id']} (score: {result['score']})")
    print(f"   Document: {result['document']}")
    print(f"   Content: {result['content'][:150]}...")

print("\n" + "=" * 60)
print("SEARCH TEST - 'algorithm'")
print("=" * 60)

results = search.search("algorithm", max_results=5)
print(f"\nFound {len(results)} results")
for i, result in enumerate(results, 1):
    print(f"\n{i}. {result['rule_id']} (score: {result['score']})")
    print(f"   Document: {result['document']}")
    print(f"   Content: {result['content'][:150]}...")

print("\n" + "=" * 60)
print("SPECIFIC RULE TEST - PhD_SEAS:ALGO-PREREQ-001")
print("=" * 60)

algo_rule = search.get_rule("PhD_SEAS:ALGO-PREREQ-001")
if algo_rule:
    print(f"✓ Rule found!")
    print(f"Content: {algo_rule['content'][:500]}")
else:
    print("✗ Rule NOT found in index")
