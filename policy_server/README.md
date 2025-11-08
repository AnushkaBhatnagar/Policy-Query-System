# Policy Engine MCP Server

MCP server for querying Columbia University graduate student policy documents.

## Features

- **4 Tools** for Claude to use:
  - `search_policies` - Search across all policy documents
  - `get_rule` - Retrieve specific rule by ID
  - `check_conflicts` - Check for policy conflicts
  - `get_precedence_framework` - Get precedence hierarchy

- **4 Resources** Claude can access:
  - `policy://gsas` - GSAS doctoral policies
  - `policy://isso` - ISSO F-1/J-1 policies
  - `policy://phd_seas` - SEAS CS PhD policies
  - `policy://conflicts` - Conflict metadata

- **Automatic Conflict Detection**: When searching, automatically checks for conflicts and includes precedence information

## Installation

### Prerequisites
- Python 3.10 or higher
- pip

### Setup

1. Install dependencies:
```bash
cd policy_server
pip install -r requirements.txt
```

2. Verify installation:
```bash
python server.py
# Should print: Loaded 3 documents, Indexed X rules, Loaded 16 conflicts
```

## Configuration for Claude Desktop

Add this to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "policy-engine": {
      "command": "python",
      "args": [
        "C:/Users/anush/Downloads/newconstraints/policy_server/server.py"
      ]
    }
  }
}
```

**Important**: Update the path to match your actual location.

## Testing

### Test 1: Direct Server Test
```bash
cd policy_server
python server.py
# Server should start and show: Loaded 3 documents, Indexed X rules, Loaded 16 conflicts
```

### Test 2: Claude Desktop Integration

1. Restart Claude Desktop after adding the configuration
2. Start a new conversation
3. Look for the 🔌 icon indicating MCP servers are connected
4. Try these test queries:

**Test Query 1**: Basic search
```
What are the defense registration requirements for PhD students?
```

Expected: Claude should use `search_policies` tool and return relevant rules from GSAS and PhD_SEAS.

**Test Query 2**: Conflict detection
```
I'm a PhD student in Computer Science on F-1 visa. Can I defend my thesis while on OPT?
```

Expected: Claude should:
- Use `search_policies` to find defense and OPT rules
- Detect conflicts between GSAS, PhD_SEAS, and ISSO policies
- Use `get_precedence_framework` to determine ISSO takes precedence
- Explain that international students need to consult ISSO

**Test Query 3**: Specific rule lookup
```
What does rule GSAS:DEFENSE-REG-001 say?
```

Expected: Claude should use `get_rule` to retrieve the specific rule.

**Test Query 4**: Precedence
```
For SEAS PhD students, do SEAS rules or GSAS rules apply for registration?
```

Expected: Claude should use `get_precedence_framework` and explain that SEAS rules override GSAS for SEAS departments.

## Tools Reference

### search_policies
```json
{
  "query": "defense registration requirements",
  "department": "PHD_SEAS",  // Optional: GSAS, ISSO, or PHD_SEAS
  "max_results": 5           // Optional: default 5
}
```

Returns:
- Matching rules with relevance scores
- Automatically includes any detected conflicts
- Includes precedence information

### get_rule
```json
{
  "rule_id": "GSAS:DEFENSE-REG-001"
}
```

Returns:
- Full rule content
- Associated conflicts (if any)

### check_conflicts
```json
{
  "rule_ids": ["GSAS:DEFENSE-REG-001", "PhD_SEAS:DEFENSE-REG-001"]
}
```

Returns:
- List of conflicts involving these rules
- Conflict metadata (type, severity, resolution logic)

### get_precedence_framework
No parameters required.

Returns:
- Precedence hierarchy (Federal > School > University)
- Explicit override statements
- Jurisdiction descriptions

## Architecture

```
policy_server/
├── server.py              # Main MCP server
├── requirements.txt       # Python dependencies
└── README.md             # This file

Project root:
├── documents/
│   ├── gsas.txt          # GSAS policies (source of truth)
│   ├── isso.txt          # ISSO policies (source of truth)
│   └── phd_seas.txt      # PhD_SEAS policies (source of truth)
└── conflicts.json        # Conflict metadata
```

## How It Works

1. **Server Startup**:
   - Loads all three policy documents
   - Extracts and indexes all rules (209 total)
   - Loads conflict metadata

2. **Search Process**:
   - Keyword-based matching with relevance scoring
   - Boosts scores for domain-specific keywords
   - Returns top N results

3. **Conflict Detection**:
   - Automatically checks if returned rules have known conflicts
   - Includes conflict metadata in response
   - Claude uses precedence framework to resolve

4. **Claude Integration**:
   - Claude calls tools as needed
   - Reasons about conflicts using precedence info
   - Provides accurate, context-aware responses

## Token Efficiency

Typical query token usage:
- User query: ~50 tokens
- Tool call: ~100 tokens
- Rule results: ~400-800 tokens (2-5 rules)
- Conflict metadata: ~200-400 tokens
- Precedence framework: ~100 tokens
- **Total per query: ~850-1,450 tokens**

Much more efficient than sending all 40KB of documents on every request.

## Troubleshooting

### Server won't start
- Check Python version: `python --version` (need 3.10+)
- Install MCP: `pip install mcp`
- Check file paths in configuration

### Claude Desktop not connecting
- Verify configuration file path
- Check JSON syntax (no trailing commas)
- Restart Claude Desktop completely
- Check Claude Desktop logs for errors

### No results from search
- Server may not have loaded documents correctly
- Check that documents/ folder is in correct location
- Verify rule IDs follow pattern: `DEPT:NAME-001`

### Conflicts not detected
- Check conflicts.json is in project root
- Verify rule IDs in conflicts.json match actual rule IDs
- Run extract_conflicts.py to regenerate if needed

## Development

To modify or extend the server:

1. **Add new search features**: Edit `PolicySearch.search()` method
2. **Add new tools**: Add to `list_tools()` and `call_tool()`
3. **Add new resources**: Add to `list_resources()` and `read_resource()`
4. **Improve scoring**: Modify keyword weights in `search()` method

## Next Steps

After verifying the server works:
1. Test with real student scenarios
2. Refine search keywords based on common queries
3. Consider adding semantic search for better accuracy
4. Add caching for frequently accessed rules
5. Build a web UI (optional)

## Support

For issues or questions about:
- **MCP protocol**: See https://modelcontextprotocol.io/
- **Claude Desktop**: See Claude Desktop documentation
- **This server**: Check server.py comments or modify as needed
