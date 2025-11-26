# MCP Server Setup for Policy Query System

## Overview

The MCP (Model Context Protocol) server provides search capabilities across your policy documents. It indexes your fully annotated policy documents and makes them searchable via Cline.

## What Was Installed

```
newconstraints/
├── mcp-server/                    ✅ MCP Server (Node.js)
│   ├── build/
│   │   └── index.js              ← Compiled server (what Cline runs)
│   ├── src/
│   │   └── index.ts              ← TypeScript source
│   ├── node_modules/             ← Dependencies (already installed)
│   └── package.json
├── documents/                     ✅ Your annotated documents
│   ├── gsas.txt (59KB)
│   ├── isso.txt (40KB)
│   └── phd_seas.txt (95KB)
└── cline_mcp_settings.json       ✅ Configuration file
```

## Step 1: Add MCP Server to Cline

### Option A: Via Cline Settings UI (Recommended)

1. Open VS Code Command Palette: `Ctrl+Shift+P` (Windows) or `Cmd+Shift+P` (Mac)
2. Type: **"Cline: Open MCP Settings"**
3. Click on the settings file that opens
4. Copy the content from `cline_mcp_settings.json` into the MCP settings
5. Save the file

### Option B: Manual Configuration

Open Cline's MCP settings file (usually at `C:\Users\anush\AppData\Roaming\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`) and add:

```json
{
  "mcpServers": {
    "policy-docs": {
      "command": "node",
      "args": [
        "C:\\Users\\anush\\Downloads\\newconstraints\\mcp-server\\build\\index.js"
      ],
      "disabled": false
    }
  }
}
```

## Step 2: Restart VS Code

**Close and reopen VS Code** to load the MCP server.

## Step 3: Test the MCP Server

### Test 1: Ask Cline to List Documents

In Cline chat, type:
```
Use the policy-docs MCP server to list all documents
```

**Expected output:**
```json
{
  "documents": [
    {"name": "gsas.txt", "pages": 1, "sections": XX},
    {"name": "isso.txt", "pages": 1, "sections": XX},
    {"name": "phd_seas.txt", "pages": 1, "sections": XX}
  ],
  "total": 3
}
```

### Test 2: Search for Algorithms Prerequisite

In Cline chat, type:
```
Use the policy-docs MCP server to search for "algorithms prerequisite"
```

**Expected:** Should return the full `[RULE:PhD_SEAS:ALGO-PREREQ-001]` with all timing details, form submission deadlines, and CSOR W4231 requirements.

### Test 3: Complex Query

In Cline chat, type:
```
Use the policy-docs MCP server to search for "M&F registration international students"
```

**Expected:** Should return relevant sections about Matriculation & Facilities registration rules and international student requirements.

## Step 4: Use with Your Application

The MCP server also provides an HTTP API on port 3000:

```bash
# Start the server directly (optional - mainly for Cline use)
cd C:\Users\anush\Downloads\newconstraints\mcp-server
node build/index.js

# Test via HTTP
curl http://localhost:3000/health
curl -X POST http://localhost:3000/api/search -H "Content-Type: application/json" -d "{\"query\": \"algorithms prerequisite\"}"
```

## How It Works

1. **Document Loading:** On startup, the MCP server:
   - Reads all `.txt` files from `documents/` folder
   - Parses your annotated content with RULE tags
   - Splits into searchable sections (~400-800 chars each)

2. **Search Algorithm:**
   - Keyword-based matching (fast & reliable)
   - Scores sections based on term frequency
   - Returns top 10 results by default
   - Deduplicates results

3. **Integration with Cline:**
   - Cline can call the MCP server via the `search_policies` tool
   - Results are returned with full context
   - You can then analyze results and answer user queries

## Troubleshooting

### Issue: "Documents directory not found"
**Solution:** Check that `documents/` folder exists with your annotated txt files.

### Issue: "Connection refused" or server won't start
**Solution:** 
1. Verify Node.js is installed: `node --version` (should show v18+)
2. Check the path in `cline_mcp_settings.json` is correct
3. Restart VS Code

### Issue: Still getting "insufficient information"
**Solution:**
1. Verify documents in `documents/` folder are the LARGE annotated ones (40-95KB)
2. Not the old condensed versions (9-10KB)
3. Check file sizes: `dir documents`
4. Restart VS Code to reload MCP server

### Issue: Search returns empty results
**Solution:**
1. Check documents loaded: Ask Cline to "list documents"
2. Verify search terms: Try simpler keywords first
3. Check document encoding: Files should be UTF-8

## Advanced Usage

### Updating Documents

When you modify policy documents:
1. Save the changes to `documents/` folder
2. Restart VS Code (or restart MCP server)
3. MCP server will reload and re-index

### Adding More Documents

Simply add new `.txt` files to the `documents/` folder. The MCP server will automatically index them on next startup.

### Changing Port (HTTP API)

Set environment variable before starting:
```bash
set HTTP_PORT=5000
node build/index.js
```

## Next Steps

1. ✅ **MCP Server Setup** - Complete!
2. 🔄 **Test with Cline** - Ask Cline to search policies
3. 📝 **Document Your Queries** - Keep track of what works well
4. 🚀 **Build Your Application** - Use this as backend for policy queries

## Support

- **MCP Server Code:** `mcp-server/build/index.js`
- **Configuration:** `cline_mcp_settings.json`
- **Documents:** `documents/` folder
- **Python Backend:** `policy_server/server.py` (separate system)

---

**Status:** ✅ MCP Server installed and configured  
**Location:** `C:\Users\anush\Downloads\newconstraints\mcp-server`  
**Documents:** 3 fully annotated policy files (195KB total)
