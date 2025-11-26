# Transcript Analyzer - Course Import Eligibility

AI-powered tool to analyze transcripts and determine course import eligibility for Columbia CS PhD program.

## Features

- **Structured Text Input**: Fill in comprehensive template with all required fields
- **Image Upload**: Upload transcript images (JPG, PNG, GIF, WEBP)
- **AI Analysis**: Claude Sonnet 4 checks all import rules
- **Detailed Results**: Per-course eligibility with reasoning and admin requirements

## Complete Import Rules Applied

### Required Conditions (ALL must be met):
1. **Grade**: B+ or better
2. **Timing**: Within past 5 years (from current year)
3. **Level**: Graduate course OR upper-division undergraduate
4. **Course Type**: Lecture course (NOT seminar, project, reading, fieldwork)
5. **Transcript**: Listed as graduate course on official transcript
6. **Credit**: Full-length course granting degree credit
7. **Enrollment Timing**: If taken DURING Columbia PhD, no Columbia equivalent exists
8. **No Duplicates**: Not importing multiple courses on same subject
9. **Exclusivity**: Not using both imported + Columbia course on same subject

## Input Template

Students provide structured information:

```
UNIVERSITY: [Name]
DEGREE PROGRAM: [e.g., MS Computer Science]

=== COURSE 1 ===
Course Number: [e.g., CS 5800]
Course Name: [e.g., Algorithms]
Department: [e.g., Computer Science]
Course Type: [Lecture / Seminar / Project / Other]
Level: [Undergraduate / Graduate]
Year Taken: [YYYY]
Semester: [Fall / Spring / Summer]
Grade: [Letter grade]
Listed as Graduate on Transcript?: [Yes / No]
Taken: [Before Columbia PhD / During Columbia PhD]
Columbia Has Equivalent Course?: [Yes / No / Unknown]
Importing Other Courses on Same Topic?: [Yes / No]
```

## Usage

### Web Interface

1. Navigate to `http://localhost:5000/transcript.html`
2. **Text Input Tab**: Fill in the structured template
3. **OR File Upload Tab**: Upload transcript image (JPG/PNG/GIF/WEBP only)
4. Click "Analyze Courses" or "Analyze Image"
5. Review detailed eligibility results with warnings

### API Usage

**Endpoint:** `POST /api/transcript/analyze`

**Text Input:**
```bash
curl -X POST http://localhost:5000/api/transcript/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "NORTHEASTERN UNIVERSITY\nMaster of Science\n\nFall 2021\nCS 5800 Algorithms Grade: A\n..."
  }'
```

**File Upload (Images Only):**
```bash
curl -X POST http://localhost:5000/api/transcript/analyze \
  -F "file=@transcript.jpg"
```

**Note:** PDFs not supported. Use images or text input.

**Response Format:**
```json
{
  "courses": [
    {
      "name": "Algorithms",
      "number": "CS 5800",
      "grade": "A",
      "year": "2021",
      "semester": "Fall",
      "level": "graduate",
      "course_type": "lecture",
      "eligible": true,
      "checks": {
        "grade_ok": true,
        "timing_ok": true,
        "level_ok": true,
        "course_type_ok": true,
        "on_transcript": true,
        "columbia_equivalent_ok": true,
        "no_duplicates": true
      },
      "reasoning": "All requirements met: Grade A (exceeds B+), taken in 2021 (within 5 years), graduate level, lecture course, no Columbia equivalent",
      "ineligible_reasons": [],
      "warnings": [
        "⚠️ Requires advisor approval",
        "⚠️ Requires faculty evaluation", 
        "⚠️ Requires DGS final approval"
      ]
    }
  ],
  "summary": {
    "total": 10,
    "eligible": 8,
    "ineligible": 2
  },
  "next_steps": "All eligible courses require: 1) Advisor approval, 2) Faculty evaluation, 3) DGS concurrence"
}
```

## Important Notes

### Student-Verifiable vs Admin Requirements

**Student answers these** (checked by AI):
- Grade received
- Year taken
- Course type
- Graduate/undergraduate level
- Listed on transcript as graduate
- Timing relative to Columbia enrollment
- Columbia equivalents
- Duplicate subjects

**Admin must verify** (shown as warnings):
- Advisor approval
- Faculty evaluation
- DGS final concurrence

## Technical Details

- **Model**: Claude Sonnet 4 (claude-sonnet-4-5-20250929)
- **Vision Support**: Images only (JPG, PNG, GIF, WEBP)
- **Max Tokens**: 4096 (handles long transcripts)
- **Temperature**: 0 (consistent, deterministic analysis)
- **PDF Support**: ❌ Not supported (convert to image or use text input)

## Limitations

1. **AI Interpretation**: Edge cases need human review
2. **Images Only**: No PDF support (technical limitation)
3. **Student-Provided Data**: Accuracy depends on correct input
4. **Preliminary Only**: Final approval requires admin verification
5. **Always verify** with academic advisor before making decisions

## Future Enhancements

- [ ] PDF text extraction support
- [ ] Confidence scoring per rule check
- [ ] Batch processing multiple courses
- [ ] Export results to PDF/Excel
- [ ] Integration with course import form
- [ ] Learning from historical approvals/rejections
