#!/usr/bin/env python3
"""Test transcript analyzer API"""

import requests
import json

# Read sample transcript
with open('test_transcript.txt', 'r') as f:
    transcript_text = f.read()

print("="*60)
print("Testing Transcript Analyzer API")
print("="*60)

# Test text input
print("\n1. Testing with text input...")
print(f"Transcript length: {len(transcript_text)} characters")

try:
    response = requests.post(
        'http://localhost:5000/api/transcript/analyze',
        json={'text': transcript_text},
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print("✓ API call successful!")
        print(f"\nResponse summary:")
        
        if 'courses' in result:
            print(f"  Courses found: {len(result['courses'])}")
            for course in result['courses']:
                status = "✓" if course.get('eligible') else "✗"
                print(f"  {status} {course.get('number', 'N/A')} - {course.get('name', 'Unknown')}")
                print(f"     Grade: {course.get('grade')}, Level: {course.get('level')}")
                if not course.get('eligible') and course.get('ineligible_reasons'):
                    print(f"     Issues: {', '.join(course['ineligible_reasons'])}")
        
        if 'summary' in result:
            print(f"\nSummary:")
            print(f"  Total: {result['summary'].get('total', 0)}")
            print(f"  Eligible: {result['summary'].get('eligible', 0)}")
        
        # Save full result
        with open('test_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Full result saved to test_result.json")
        
    else:
        print(f"✗ API returned status {response.status_code}")
        print(f"Error: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("✗ Could not connect to server")
    print("Make sure the webapp is running: python webapp/app.py")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "="*60)
print("Test complete!")
