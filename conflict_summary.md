# Policy Conflict Analysis Summary

## Overview
- **Total Documents Analyzed**: 3
- **Total Rules Parsed**: 209
- **Rules with Conflict Annotations**: 16

## Conflicts by Jurisdiction

### GSAS (University Level - Precedence 3): 5 conflicts
1. **GSAS:AUTHORITY-001** - Authority split between GSAS and SEAS
2. **GSAS:PROSPECTUS-DEADLINE-001** - Timing conflict with PhD_SEAS
3. **GSAS:DEFENSE-LAST-REG-001** - Registration timing for international students
4. **GSAS:DEFENSE-CLOSED-001** - Defense format conflict (closed vs public seminar)
5. **GSAS:PROSPECTUS-DEADLINE-REPEAT-001** - Duplicate rule

### ISSO (Federal Level - Precedence 1): 4 conflicts
1. **ISSO:RCL-001** - Reduced course load vs academic program requirements
2. **ISSO:TRAVEL-SIG-001** - Travel signature validity (12 months vs 6 during OPT)
3. **ISSO:LOA-TERMINATION-001** - 15-day departure vs academic semester timing
4. **ISSO:OPT-TRAVEL-001** - Shorter validity during OPT (6 months vs 12)

### PhD_SEAS (School Level - Precedence 2): 7 conflicts
1. **PhD_SEAS:CANDIDACY-001** - Candidacy exam timing vs GSAS prospectus timing
2. **PhD_SEAS:GSAS-SEAS-001** - **EXPLICIT OVERRIDE**: SEAS rules override GSAS for SEAS departments
3. **PhD_SEAS:REG-001** - Point system (15 points) vs RU system
4. **PhD_SEAS:GSAS-RU-001** - Registration system differences
5. **PhD_SEAS:ER-001** - Extended Residence eligibility differences
6. **PhD_SEAS:MF-001** - **EXPLICIT OVERRIDE**: SEAS M&F rules override GSAS
7. **PhD_SEAS:SUMMER-DEFENSE-001** - Summer registration exception

## Key Findings

### Explicit Override Statements Found
Two rules contain explicit precedence declarations:
- **PhD_SEAS:GSAS-SEAS-001**: "SEAS rules override GSAS rules for SEAS departments"
- **PhD_SEAS:MF-001**: "SEAS rules contradict and override the GSAS rules"

### Conflict Categories

#### 1. Timing Conflicts (4)
- Prospectus/Proposal deadlines: May 31 year 4 (GSAS) vs 8th semester (PhD_SEAS)
- Candidacy exam vs prospectus timing
- Travel signature validity periods
- Leave of absence departure deadlines

#### 2. Registration System Conflicts (4)
- Point system (15 points) vs Residence Unit system (1 RU)
- Full-time definition variations: 12 points, 15 points, or 1 RU
- Extended Residence vs Matriculation & Facilities eligibility
- Summer registration requirements

#### 3. Defense Format Conflicts (2)
- Closed defense (GSAS) vs public seminar requirement (PhD_SEAS)
- Defense registration requirements for international students

#### 4. Authority/Administration Conflicts (2)
- GSAS confers degree, SEAS administers programs
- Academic program requirements vs immigration requirements

#### 5. Status/Eligibility Conflicts (4)
- Reduced course load exceptions
- OPT eligibility after leave of absence
- Travel document validity periods
- Student status during defense

## Priority Conflicts (Need Resolution Documentation)

### CRITICAL (Affect legal status/degree eligibility)
1. **Registration requirements for international students on OPT**
   - Rules: ISSO:ENROLLMENT-001, GSAS:DEFENSE-REG-001, PhD_SEAS:DEFENSE-REG-001
   - Impact: Visa compliance vs degree completion

2. **Leave of absence departure timing**
   - Rules: ISSO:LOA-TERMINATION-001 (15 days) vs academic semester schedules
   - Impact: Forced departure mid-semester

### HIGH (Affect timeline/milestones)
3. **Prospectus/Proposal deadline**
   - Rules: GSAS:PROSPECTUS-DEADLINE-001 (May 31 year 4) vs PhD_SEAS:PROPOSAL-001 (8th semester)
   - Impact: Different timelines for SEAS students

4. **Registration systems**
   - Rules: PhD_SEAS:REG-001 (15 points) vs GSAS (1 RU) vs ISSO:ENROLLMENT-001 (12 points minimum)
   - Impact: Compliance complexity

5. **Defense format**
   - Rules: GSAS:DEFENSE-CLOSED-001 (closed) vs PhD_SEAS:DEFENSE-SEMINAR-001 (public seminar)
   - Impact: Contradictory requirements

### MEDIUM (Administrative confusion)
6. **Travel signature validity**
   - Rules: ISSO:TRAVEL-SIG-001 (12 months) vs ISSO:OPT-TRAVEL-001 (6 months during OPT)
   - Impact: Travel documentation confusion

7. **Matriculation & Facilities eligibility**
   - Rules: GSAS:MF-001 vs PhD_SEAS:MF-001
   - Impact: Registration options differ by department

## Next Steps: Phase 3 - Conflict Resolution Documentation

For each conflict, we need to document:
1. **Which rule takes precedence and why**
2. **Under what conditions each applies**
3. **Specific student populations affected**
4. **Clear guidance for resolution**

### Precedence Framework Already Identified:
- **Level 1 (Federal)**: ISSO rules - Always takes precedence (immigration law)
- **Level 2 (School)**: PhD_SEAS rules - Takes precedence over GSAS for SEAS students
- **Level 3 (University)**: GSAS rules - Default for non-SEAS departments

### Resolution Template Example:
```
CONFLICT ID: C001
RULES INVOLVED: GSAS:PROSPECTUS-DEADLINE-001, PhD_SEAS:PROPOSAL-001
ISSUE: Different deadlines (May 31 year 4 vs 8th semester)
RESOLUTION: For SEAS PhD students → PhD_SEAS timeline (8th semester)
            For non-SEAS students → GSAS timeline (May 31 year 4)
JUSTIFICATION: PhD_SEAS:GSAS-SEAS-001 explicitly states SEAS rules override
APPLIES TO: Determined by home department
SPECIAL CASES: Off-cycle students may have adjusted dates per GSAS rules
```

## Files Generated
- `conflicts.json` - Complete structured data
- `conflict_summary.md` - This human-readable summary

## Statistics
- **Average conflicts per document**: 5.3
- **Rules with SEE-ALSO references**: 16
- **Rules with explicit overrides**: 2
- **Highest conflict jurisdiction**: PhD_SEAS (7 conflicts)
