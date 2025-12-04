# Test Case: Signature Assumption Problem

## Problem Identified

The AI was making incorrect assumptions about roles based on names alone, leading to wrong conclusions about form completion.

## Original Query (Problematic)

```
Daria went to Lomonosov Moscow State University and earned the equivalent of both a bachelor's and master's degrees. She has English translations and an official degree evaluation.

The problem is none of the documents provide information about individual courses. I can't tell what is and isn't graduate level or upper-level undergraduate. 

Daria resubmitted her import with a document that shows she completed the course during her third year in that program, which was fall 2020. Cliff signed the import request. Is this sufficient information to approve the algorithms import?
```

## What the AI Did Wrong (Before Fix)

❌ Assumed "Cliff signed" meant Cliff is the advisor
❌ Made approval decision based on incomplete information
❌ Didn't recognize that 2 signatures are required from 2 different people

**AI's problematic response:**
> "Cliff (advisor) signed the import request..."

## What the AI Should Do (After Fix)

✓ Recognize that signature information is ambiguous
✓ Know that algorithms prerequisite requires TWO signatures:
  1. Student's advisor
  2. Algorithms instructor/evaluator
✓ Ask for clarification about Cliff's role
✓ State that information is insufficient

**Expected corrected response:**
> "The information doesn't specify whether Cliff is Daria's advisor or the algorithms instructor. The algorithms prerequisite form requires TWO signatures from TWO different people:
> 1. The student's advisor
> 2. The algorithms course evaluator (instructor)
> 
> To evaluate whether this is sufficient, I need clarification:
> - What is Cliff's role? Is he Daria's advisor or the algorithms instructor at Columbia?
> - If Cliff is one of these, has the other required signature been obtained?
> 
> [Citation: PhD_SEAS:ALGO-PREREQ-SIGNATURES-001]"

## Changes Made to Fix

### 1. New Policy Document
Created `documents/algo_prereq_signatures.txt` with explicit rules:
- `PhD_SEAS:ALGO-PREREQ-SIGNATURES-001` - TWO signatures required
- `PhD_SEAS:ALGO-PREREQ-SIGNATURE-ROLES-001` - How to verify signatures

### 2. Updated System Prompt
Added to `webapp/app.py`:

```python
CRITICAL: DO NOT MAKE ASSUMPTIONS

When evaluating approvals, signatures, or requirements:
- NEVER assume someone's role from their name alone
- NEVER assume one signature fulfills multiple requirements
- If signature/approval requirements exist, verify ALL are present
- If information about WHO signed/approved is ambiguous, EXPLICITLY state: 
  "The information doesn't specify whether [person] is the [role1] or [role2]. 
  Clarification needed on [person]'s role."
- When multiple signatures/approvals required from different roles, 
  verify EACH role separately

Example of what NOT to do:
❌ "Cliff signed the import request" → assuming Cliff is the advisor
✓ "Cliff signed, but it's unclear whether Cliff is the student's advisor 
   or the algorithms instructor. Both signatures are required from two 
   different people."
```

### 3. Updated Policy Server
Modified `policy_server/server.py` to load the new signatures document.

## Test Queries

### Test 1: Ambiguous Single Signature
**Query:** "John signed the algorithms prerequisite form. Can we approve it?"

**Expected Response:**
- Search for algorithms prerequisite signature requirements
- Find PhD_SEAS:ALGO-PREREQ-SIGNATURES-001
- State: "Insufficient information. Need to know:
  1. Is John the student's advisor or the algorithms instructor?
  2. Has the second required signature been obtained?
  Both signatures from two different people are required."

### Test 2: Only Advisor Signature Mentioned
**Query:** "The student's advisor approved the algorithms import. Is that enough?"

**Expected Response:**
- State: "No, that's not sufficient. Two signatures are required:
  1. Advisor (✓ obtained)
  2. Algorithms instructor/evaluator (? not mentioned)
  Both must be present for approval."

### Test 3: Complete Information
**Query:** "Both the student's advisor (Dr. Smith) and the algorithms instructor (Prof. Johnson) signed the prerequisite form. Grade was A-, course was from 2023. Can we approve?"

**Expected Response:**
- Both signatures confirmed: ✓
- Different people: ✓
- Should proceed to check other requirements (grade, timing, etc.)
- Provide comprehensive approval/rejection with all criteria

## Verification Checklist

After deploying the fix, verify:
- [ ] System searches for and finds signature requirement rules
- [ ] System doesn't assume roles from names alone
- [ ] System explicitly asks for clarification when information is ambiguous
- [ ] System verifies BOTH required signatures separately
- [ ] System only approves when ALL requirements are explicitly confirmed

## Related Rules

- `PhD_SEAS:ALGO-PREREQ-001` - General algorithms prerequisite requirements
- `PhD_SEAS:ALGO-PREREQ-SIGNATURES-001` - Signature requirements (NEW)
- `PhD_SEAS:ALGO-PREREQ-SIGNATURE-ROLES-001` - Signature verification process (NEW)
- `PhD_SEAS:ALGO-PREREQ-FORM-TIMING-001` - Form submission timing (NEW)
