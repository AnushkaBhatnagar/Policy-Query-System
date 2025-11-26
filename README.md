# Policy Query System

An intelligent policy query system leveraging Claude AI with MCP (Model Context Protocol) integration for natural language policy search and conflict resolution.

## Overview

This project demonstrates an **agentic LLM workflow** where Claude Sonnet 4.5 uses MCP tools to search and analyze Columbia University PhD policies. The system showcases how LLMs can leverage external tools to provide accurate, context-aware responses with proper source attribution.

## Core Architecture: LLM + MCP

### How It Works

```
User Query
    ↓
Claude Sonnet 4.5 (LLM Agent)
    ↓
Decides to use search_policies tool
    ↓
MCP Server (Tool Provider)
    ↓
TF-IDF Search + Conflict Detection
    ↓
Returns policy rules to Claude
    ↓
Claude synthesizes response
```

### Key Components

**1. Claude as Intelligent Agent**
- Analyzes user queries
- Decides which MCP tools to call
- Iteratively searches until sufficient information gathered
- Synthesizes responses with proper citations
- Detects when multiple departments have conflicting rules

**2. MCP Server (Tool Provider)**
- Provides `search_policies` tool to Claude
- Indexes 200+ annotated policy rules
- Implements TF-IDF vectorization for semantic search
- Returns matching rules with metadata (jurisdiction, precedence, conflicts)
- Additional tools: `get_rule`, `check_conflicts`, `get_precedence_framework`

**3. Agentic Workflow**
- Claude calls tools multiple times per query (average: 3-5 iterations)
- Tool results inform next tool calls
- Continues until Claude determines sufficient information gathered
- No hardcoded logic - Claude decides the search strategy

### MCP Tool Schema Example

```python
{
    "name": "search_policies",
    "description": "Search across all policy documents for relevant rules",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "department": {"type": "string", "enum": ["GSAS", "ISSO", "PHD_SEAS"]},
            "max_results": {"type": "number"}
        }
    }
}
```

## Technical Stack

**LLM Layer:**
- Anthropic Claude Sonnet 4.5
- Tool use (function calling)
- Structured prompting with system instructions

**MCP Layer:**
- Custom MCP server in Python
- PolicySearch class with TF-IDF vectorization
- Conflict detection engine
- Hierarchical precedence framework

**Web Layer:**
- Flask (Python web framework)
- Response caching (24hr TTL)
- Session management for multi-turn conversations
- Google Sheets logging

**Policy Documents:**
- 3 departments: GSAS, ISSO, PhD SEAS
- 200+ annotated rules with structured metadata
- Conflict annotations and precedence rules

## Conflict Resolution

The system implements a hierarchical precedence framework:

1. **Federal (ISSO)** - Immigration law, always takes precedence
2. **School (PhD SEAS)** - SEAS policies override GSAS for engineering students
3. **University (GSAS)** - Default policies

When conflicts detected, Claude receives both conflicting rules plus resolution logic and synthesizes the correct answer based on student's context.

## Installation

### Prerequisites
- Python 3.11+
- Anthropic API key

### Setup

```bash
# Clone repo
git clone <repo-url>
cd newconstraints

# Install dependencies
pip install -r webapp/requirements.txt

# Configure environment
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env

# Run
python webapp/app.py
```

Open `http://localhost:5000`

## Environment Variables

```bash
ANTHROPIC_API_KEY=your_key_here
GOOGLE_SHEET_ID=optional_for_logging
GOOGLE_CREDENTIALS=optional_for_logging
```

## API

**POST /api/query**
```json
{
  "query": "Your question",
  "session_id": "optional"
}
```

**POST /api/batch**
Process multiple queries

**POST /api/transcript/analyze**
Analyze course transcripts (uses Claude Vision)

## Project Structure

```
newconstraints/
├── documents/           # Annotated policy documents
├── policy_server/       # MCP server implementation
├── webapp/             # Flask application
│   ├── app.py          # Main application + Claude integration
│   └── static/         # Frontend
├── conflicts.json      # Conflict rules and precedence
└── .env.example        # Environment template
```

## Key Features

**LLM-Powered:**
- Natural language understanding
- Contextual query interpretation
- Multi-turn conversations with memory
- Automatic source citation

**MCP Integration:**
- Claude calls tools as needed
- No hardcoded search logic
- Iterative refinement
- Tool results guide next steps

**Policy Intelligence:**
- Conflict detection across departments
- Precedence-based resolution
- Structured rule annotations
- Metadata-rich responses

## Deployment

**Render:**
1. Connect GitHub repository
2. Add environment variables
3. Auto-deploys on push

**Configuration:**
- Python 3.11 (runtime.txt)
- Auto build from requirements.txt
- Start: `python webapp/app.py`
