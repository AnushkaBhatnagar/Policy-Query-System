#!/usr/bin/env python3
"""
Policy Query Web Application
Simple Flask app that connects to MCP server and Claude API
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory
from anthropic import Anthropic
import logging
from dotenv import load_dotenv
import gspread

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_ENABLED = True
CACHE_TTL = timedelta(hours=24)  # Cache for 24 hours
MAX_CACHE_SIZE = 1000  # Maximum number of cached queries

# Cache storage
QUERY_CACHE = {}
cache_hits = 0
cache_misses = 0

# Conversation storage
CONVERSATIONS = {}  # session_id: [messages]

# Google Sheets logging
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
SHEETS_ENABLED = True
sheets_client = None

def init_google_sheets():
    """Initialize Google Sheets client."""
    global sheets_client, SHEETS_ENABLED
    try:
        # Try environment variable first (for Render deployment)
        google_creds = os.environ.get('GOOGLE_CREDENTIALS')
        if google_creds:
            credentials_dict = json.loads(google_creds)
            sheets_client = gspread.service_account_from_dict(credentials_dict)
            logger.info("✓ Google Sheets logging enabled (from environment variable)")
            return True
        
        # Fall back to credentials.json file (for local development)
        credentials_path = Path(__file__).parent / 'credentials.json'
        if credentials_path.exists():
            sheets_client = gspread.service_account(filename=str(credentials_path))
            logger.info("✓ Google Sheets logging enabled (from credentials file)")
            return True
        
        logger.warning("No Google credentials found - Google Sheets logging disabled")
        SHEETS_ENABLED = False
        return False
        
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets: {e}")
        SHEETS_ENABLED = False
        return False

def log_to_sheets(session_id, query, response, tool_uses, iterations, cached):
    """Log query and response to Google Sheets."""
    if not SHEETS_ENABLED or not sheets_client:
        return
    
    try:
        sheet = sheets_client.open_by_key(SHEET_ID).sheet1
        
        # Format tool uses as comma-separated names
        tool_names = ', '.join([t['name'] for t in tool_uses]) if tool_uses else 'None'
        
        # Append row to sheet
        sheet.append_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            session_id,
            query,
            response[:5000],  # Limit response length for sheets
            tool_names,
            iterations,
            'Yes' if cached else 'No'
        ])
        
        logger.info("✓ Logged to Google Sheets")
    except Exception as e:
        logger.error(f"Failed to log to Google Sheets: {e}")

app = Flask(__name__, static_folder='static', static_url_path='')

# Initialize Anthropic client
client = None
try:
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
except Exception as e:
    logger.error(f"Failed to initialize Anthropic client: {e}")

# Pre-load MCP server components at startup
MCP_LOADED = False
SEARCH_ENGINE = None

def init_mcp_server():
    """Initialize MCP server components at startup."""
    global MCP_LOADED, SEARCH_ENGINE
    try:
        server_path = Path(__file__).parent.parent / "policy_server" / "server.py"
        import sys
        sys.path.insert(0, str(server_path.parent))
        
        from server import PolicySearch, DOCUMENTS, CONFLICTS, load_documents, RULE_INDEX
        
        # Load documents
        load_documents()
        
        if not DOCUMENTS:
            logger.error("Failed to load policy documents!")
            return False
        
        # Create search engine
        SEARCH_ENGINE = PolicySearch(DOCUMENTS, CONFLICTS)
        MCP_LOADED = True
        
        logger.info(f"✓ MCP Server initialized: {len(DOCUMENTS)} documents loaded")
        logger.info(f"✓ Rule index built: {len(RULE_INDEX)} rules indexed")
        if RULE_INDEX:
            sample_rules = list(RULE_INDEX.keys())[:5]
            logger.info(f"  Sample rule IDs: {sample_rules}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {e}")
        return False

# MCP tool definitions
MCP_TOOLS = [
    {
        "name": "search_policies",
        "description": "Search across all policy documents for relevant rules. Returns matching rules with metadata and any known conflicts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (keywords or natural language)"
                },
                "department": {
                    "type": "string",
                    "description": "Filter by department: GSAS, ISSO, or PHD_SEAS",
                    "enum": ["GSAS", "ISSO", "PHD_SEAS"]
                },
                "max_results": {
                    "type": "number",
                    "description": "Maximum number of results (default: 5)",
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_rule",
        "description": "Get full details of a specific rule by its ID (e.g., GSAS:DEFENSE-REG-001)",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_id": {
                    "type": "string",
                    "description": "Rule ID (e.g., GSAS:DEFENSE-REG-001)"
                }
            },
            "required": ["rule_id"]
        }
    },
    {
        "name": "check_conflicts",
        "description": "Check if given rules have any known conflicts and get precedence information",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of rule IDs to check for conflicts"
                }
            },
            "required": ["rule_ids"]
        }
    },
    {
        "name": "get_precedence_framework",
        "description": "Get the precedence hierarchy and explicit override rules",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]


def call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Call MCP server tool using pre-loaded search engine.
    """
    global SEARCH_ENGINE
    
    try:
        # Use pre-loaded search engine or initialize if needed
        if not SEARCH_ENGINE:
            logger.warning("Search engine not initialized, initializing now...")
            if not init_mcp_server():
                return {"error": "Failed to initialize MCP server"}
        
        search_engine = SEARCH_ENGINE
        
        # Get CONFLICTS for precedence framework
        from server import CONFLICTS
        
        # Call the appropriate tool
        if tool_name == "search_policies":
            query = tool_input.get("query")
            department = tool_input.get("department")
            max_results = tool_input.get("max_results", 5)
            
            logger.info(f"  🔍 Searching for: '{query}' (department: {department}, max: {max_results})")
            
            results = search_engine.search(query, department, max_results)
            result_rule_ids = [r['rule_id'] for r in results]
            conflicts = search_engine.check_conflicts(result_rule_ids)
            
            logger.info(f"  ✅ Found {len(results)} results: {result_rule_ids[:3]}...")
            if results:
                logger.info(f"  📋 Top result: {results[0]['rule_id']} (score: {results[0]['score']})")
            
            return {
                "query": query,
                "results_count": len(results),
                "results": results,
                "conflicts_detected": len(conflicts) > 0,
                "conflicts": conflicts if conflicts else None
            }
        
        elif tool_name == "get_rule":
            rule_id = tool_input.get("rule_id")
            rule = search_engine.get_rule(rule_id)
            
            if not rule:
                return {"error": f"Rule {rule_id} not found"}
            
            conflicts = search_engine.check_conflicts([rule_id])
            return {
                "rule": rule,
                "conflicts": conflicts if conflicts else None
            }
        
        elif tool_name == "check_conflicts":
            rule_ids = tool_input.get("rule_ids", [])
            conflicts = search_engine.check_conflicts(rule_ids)
            
            return {
                "rule_ids_checked": rule_ids,
                "conflicts_found": len(conflicts),
                "conflicts": conflicts
            }
        
        elif tool_name == "get_precedence_framework":
            return CONFLICTS.get('precedence_framework', {})
        
        return {"error": "Unknown tool"}
        
    except Exception as e:
        logger.error(f"Error calling MCP tool: {e}")
        return {"error": str(e)}


# Cache helper functions
def get_cache_key(query: str) -> str:
    """Generate a cache key from query text."""
    return hashlib.md5(query.lower().strip().encode()).hexdigest()


def get_cached_response(query: str) -> dict:
    """Check if query response is cached and still valid."""
    global cache_hits, cache_misses
    
    if not CACHE_ENABLED:
        return None
    
    key = get_cache_key(query)
    if key in QUERY_CACHE:
        cached = QUERY_CACHE[key]
        # Check if cache entry is still valid
        if datetime.now() - cached['timestamp'] < CACHE_TTL:
            cache_hits += 1
            logger.info(f"  ✓ Cache HIT - returning cached response")
            return cached
        else:
            # Cache expired, remove it
            del QUERY_CACHE[key]
            logger.info(f"  Cache entry expired, removing")
    
    cache_misses += 1
    logger.info(f"  Cache MISS - processing with Claude")
    return None


def cache_response(query: str, response: str, tool_uses: list, iterations: int):
    """Cache a query response."""
    if not CACHE_ENABLED:
        return
    
    # Check if cache is full and evict oldest entries
    if len(QUERY_CACHE) >= MAX_CACHE_SIZE:
        evict_old_entries()
    
    key = get_cache_key(query)
    QUERY_CACHE[key] = {
        'response': response,
        'tool_uses': tool_uses,
        'iterations': iterations,
        'timestamp': datetime.now(),
        'query': query  # Store original query for debugging
    }
    logger.info(f"  ✓ Response cached (cache size: {len(QUERY_CACHE)})")


def evict_old_entries():
    """Evict oldest cache entries when cache is full."""
    # Sort by timestamp and remove oldest 10%
    sorted_entries = sorted(
        QUERY_CACHE.items(),
        key=lambda x: x[1]['timestamp']
    )
    num_to_remove = max(1, len(sorted_entries) // 10)
    
    for i in range(num_to_remove):
        key = sorted_entries[i][0]
        del QUERY_CACHE[key]
    
    logger.info(f"  Evicted {num_to_remove} old cache entries")


# Conversation helper functions
def get_or_create_session(session_id=None):
    """Get existing session or create new one."""
    if not session_id or session_id not in CONVERSATIONS:
        session_id = str(uuid.uuid4())
        CONVERSATIONS[session_id] = []
        logger.info(f"Created new session: {session_id}")
    return session_id


def add_to_conversation(session_id, role, content):
    """Add message to conversation history."""
    if session_id not in CONVERSATIONS:
        CONVERSATIONS[session_id] = []
    
    CONVERSATIONS[session_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now()
    })


def get_conversation_history(session_id, max_messages=20):
    """Get conversation history formatted for Claude API."""
    if session_id not in CONVERSATIONS:
        return []
    
    messages = CONVERSATIONS[session_id]
    
    # Truncate to last max_messages to avoid context limits
    if len(messages) > max_messages:
        messages = messages[-max_messages:]
    
    # Format for Claude API (only role and content)
    return [{"role": msg["role"], "content": msg["content"]} 
            for msg in messages]


def clear_conversation(session_id):
    """Clear conversation history."""
    if session_id in CONVERSATIONS:
        del CONVERSATIONS[session_id]
        logger.info(f"Cleared conversation: {session_id}")


@app.route('/')
def index():
    """Serve the main page."""
    return send_from_directory('static', 'index.html')


@app.route('/api/query', methods=['POST'])
def query():
    """Handle user query and interact with Claude API."""
    if not client:
        return jsonify({
            "error": "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable."
        }), 500
    
    try:
        data = request.json
        user_query = data.get('query', '')
        session_id = data.get('session_id')
        
        if not user_query:
            return jsonify({"error": "Query is required"}), 400
        
        # Get or create session
        session_id = get_or_create_session(session_id)
        
        logger.info(f"Processing query in session {session_id}: {user_query}")
        
        # Check cache only for first message in conversation
        conversation_history = get_conversation_history(session_id)
        if len(conversation_history) == 0:
            cached = get_cached_response(user_query)
            if cached:
                # Add to conversation history
                add_to_conversation(session_id, "user", user_query)
                add_to_conversation(session_id, "assistant", cached['response'])
                
                # Log to Google Sheets
                log_to_sheets(session_id, user_query, cached['response'], 
                            cached['tool_uses'], cached['iterations'], True)
                
                return jsonify({
                    "response": cached['response'],
                    "tool_uses": cached['tool_uses'],
                    "iterations": cached['iterations'],
                    "cached": True,
                    "session_id": session_id,
                    "cache_timestamp": cached['timestamp'].isoformat()
                })
        
        # Add user message to conversation
        add_to_conversation(session_id, "user", user_query)
        
        # Get full conversation history for Claude
        messages = get_conversation_history(session_id)
        
        # Track tool uses for debugging
        tool_uses = []
        
        # Call Claude with MCP tools
        max_iterations = 15  # Increased to allow more complex queries
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"→ Iteration {iteration}/{max_iterations}")
            
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                temperature=0,
                system="""You are a Columbia University policy advisor assistant.

ADAPTIVE RESPONSE:

For DIRECT QUESTIONS:
- Direct answer
- Use [1], [2], [3] citation format for rules (list at end)
- Include contacts if available
- Concise

For SITUATIONS:
- Identify affected areas
- Search comprehensively
- Structured response:
  **Situation**
  **Affected Areas** (enrollment, visa, housing, financial aid, ER, M&F, etc.)
  **Requirements** [citations]
  **Action Plan** (with contacts)
  **Options**
  **Warnings**
  **Contacts**

CRITICAL: Always check Extended Residence (ER) and Matriculation & Facilities (M&F) options in planning scenarios.

RESEARCH:
- Search ALL related areas (enrollment, visa, housing, financial aid, ER, M&F, etc.)
- Check conflicts when multiple policies apply
- Extract contacts - emailids, phone numbers, office locations
- If information is missing or unclear: explicitly state "Documentation does not cover [topic]" or "Insufficient information available on [topic]"

OUTPUT:
- Use [1], [2] citation format (list all citations at end as "Citations: [1] RULE-ID, [2] RULE-ID")
- Flag missing information clearly
- Highlight ER/M&F when relevant
- Be concise and avoid repetition
- Under 1500 words
- Verified reasoning only (no false starts)""",
                tools=MCP_TOOLS,
                messages=messages
            )
            
            # Check if Claude wants to use tools
            if response.stop_reason == "tool_use":
                # Extract ALL tool uses from the response
                tool_use_blocks = []
                assistant_content = []
                
                for block in response.content:
                    if block.type == "tool_use":
                        tool_use_blocks.append(block)
                        tool_uses.append({
                            "name": block.name,
                            "input": block.input
                        })
                    assistant_content.append(block)
                
                if tool_use_blocks:
                    logger.info(f"  Claude wants to use {len(tool_use_blocks)} tool(s)")
                    
                    # Add assistant message with all tool uses
                    messages.append({
                        "role": "assistant",
                        "content": assistant_content
                    })
                    
                    # Call MCP server for each tool and collect all results
                    tool_results = []
                    for tool_block in tool_use_blocks:
                        logger.info(f"  Calling tool: {tool_block.name}")
                        tool_result = call_mcp_tool(
                            tool_block.name,
                            tool_block.input
                        )
                        
                        logger.info(f"  ✓ {tool_block.name} returned {len(str(tool_result))} chars")
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": json.dumps(tool_result)
                        })
                    
                    # Add all tool results in a single user message
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                    
                    # Continue loop to get Claude's response with the tool results
                    continue
            
            # If we get here, Claude has finished (no more tool use)
            # Extract final text response
            final_response = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_response += block.text
            
            logger.info(f"✓ Query completed in {iteration} iteration(s)")
            
            # Add assistant response to conversation
            add_to_conversation(session_id, "assistant", final_response)
            
            # Cache the response (only for first message)
            if len(get_conversation_history(session_id)) == 2:  # user + assistant
                cache_response(user_query, final_response, tool_uses, iteration)
            
            # Log to Google Sheets
            log_to_sheets(session_id, user_query, final_response, tool_uses, iteration, False)
            
            return jsonify({
                "response": final_response,
                "tool_uses": tool_uses,
                "iterations": iteration,
                "session_id": session_id,
                "cached": False
            })
        
        # Max iterations reached
        logger.error(f"✗ Max iterations ({max_iterations}) reached without completion")
        logger.error(f"  Total tool uses: {len(tool_uses)}")
        for i, tool_use in enumerate(tool_uses, 1):
            logger.error(f"  {i}. {tool_use['name']}")
        
        return jsonify({
            "error": f"Max iterations ({max_iterations}) reached. The query was too complex or encountered an error.",
            "tool_uses": tool_uses,
            "iterations": max_iterations
        }), 500
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/batch', methods=['POST'])
def batch_query():
    """Handle batch queries - process multiple independent queries."""
    if not client:
        return jsonify({
            "error": "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable."
        }), 500
    
    try:
        data = request.json
        queries = data.get('queries', [])
        
        if not queries:
            return jsonify({"error": "No queries provided"}), 400
        
        if len(queries) > 50:
            return jsonify({"error": "Maximum 50 queries allowed per batch"}), 400
        
        logger.info(f"Processing batch of {len(queries)} queries")
        
        start_time = datetime.now()
        results = []
        successful = 0
        failed = 0
        
        # Process each query independently
        for idx, user_query in enumerate(queries):
            logger.info(f"Processing batch query {idx + 1}/{len(queries)}: {user_query[:50]}...")
            
            try:
                # Check cache first
                cached = get_cached_response(user_query)
                if cached:
                    # Log cached response to Google Sheets
                    log_to_sheets('batch', user_query, cached['response'], 
                                cached['tool_uses'], cached['iterations'], True)
                    
                    results.append({
                        "query_index": idx + 1,
                        "query": user_query,
                        "response": cached['response'],
                        "tool_uses": cached['tool_uses'],
                        "iterations": cached['iterations'],
                        "cached": True
                    })
                    successful += 1
                    continue
                
                # Process new query (no conversation context for batch)
                messages = [{"role": "user", "content": user_query}]
                tool_uses = []
                max_iterations = 15
                iteration = 0
                
                while iteration < max_iterations:
                    iteration += 1
                    
                    response = client.messages.create(
                        model="claude-sonnet-4-5-20250929",
                        max_tokens=2048,
                        temperature=0,
                        system="""You are a Columbia University policy advisor assistant.

ADAPTIVE RESPONSE:

For DIRECT QUESTIONS:
- Direct answer
- Use [1], [2], [3] citation format for rules (list at end)
- Include contacts if available
- Concise

For SITUATIONS:
- Identify affected areas
- Search comprehensively
- Structured response:
  **Situation**
  **Affected Areas** (enrollment, visa, housing, financial aid, ER, M&F, etc.)
  **Requirements** [citations]
  **Action Plan** (with contacts)
  **Options**
  **Warnings**
  **Contacts**

CRITICAL: Always check Extended Residence (ER) and Matriculation & Facilities (M&F) options in planning scenarios.

RESEARCH:
- Search ALL related areas (enrollment, visa, housing, financial aid, ER, M&F, etc.)
- Check conflicts when multiple policies apply
- Extract contacts - emailids, phone numbers, office locations
- If information is missing or unclear: explicitly state "Documentation does not cover [topic]" or "Insufficient information available on [topic]"

OUTPUT:
- Use [1], [2] citation format (list all citations at end as "Citations: [1] RULE-ID, [2] RULE-ID")
- Flag missing information clearly
- Highlight ER/M&F when relevant
- Be concise and avoid repetition
- Under 1500 words
- Verified reasoning only (no false starts)""",
                        tools=MCP_TOOLS,
                        messages=messages
                    )
                    
                    if response.stop_reason == "tool_use":
                        tool_use_blocks = []
                        assistant_content = []
                        
                        for block in response.content:
                            if block.type == "tool_use":
                                tool_use_blocks.append(block)
                                tool_uses.append({
                                    "name": block.name,
                                    "input": block.input
                                })
                            assistant_content.append(block)
                        
                        if tool_use_blocks:
                            messages.append({
                                "role": "assistant",
                                "content": assistant_content
                            })
                            
                            tool_results = []
                            for tool_block in tool_use_blocks:
                                tool_result = call_mcp_tool(
                                    tool_block.name,
                                    tool_block.input
                                )
                                
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_block.id,
                                    "content": json.dumps(tool_result)
                                })
                            
                            messages.append({
                                "role": "user",
                                "content": tool_results
                            })
                            continue
                    
                    # Extract final response
                    final_response = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_response += block.text
                    
                    # Cache the response
                    cache_response(user_query, final_response, tool_uses, iteration)
                    
                    # Log to Google Sheets
                    log_to_sheets('batch', user_query, final_response, tool_uses, iteration, False)
                    
                    results.append({
                        "query_index": idx + 1,
                        "query": user_query,
                        "response": final_response,
                        "tool_uses": tool_uses,
                        "iterations": iteration,
                        "cached": False
                    })
                    successful += 1
                    break
                
                if iteration >= max_iterations:
                    logger.error(f"Batch query {idx + 1} reached max iterations")
                    results.append({
                        "query_index": idx + 1,
                        "query": user_query,
                        "error": "Max iterations reached",
                        "cached": False
                    })
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Error processing batch query {idx + 1}: {e}")
                results.append({
                    "query_index": idx + 1,
                    "query": user_query,
                    "error": str(e),
                    "cached": False
                })
                failed += 1
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        logger.info(f"✓ Batch complete: {successful}/{len(queries)} successful in {total_time:.1f}s")
        
        return jsonify({
            "results": results,
            "total_queries": len(queries),
            "successful": successful,
            "failed": failed,
            "total_time_seconds": total_time
        })
        
    except Exception as e:
        logger.error(f"Error processing batch: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "mcp_server": "connected",
        "claude_api": "configured" if client else "not configured"
    })


@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics."""
    total_requests = cache_hits + cache_misses
    hit_rate = cache_hits / total_requests if total_requests > 0 else 0
    
    # Calculate estimated savings
    avg_cost_per_query = 0.024  # Approximate cost per uncached query
    estimated_savings = cache_hits * avg_cost_per_query
    
    return jsonify({
        "cache_enabled": CACHE_ENABLED,
        "cache_size": len(QUERY_CACHE),
        "max_cache_size": MAX_CACHE_SIZE,
        "cache_ttl_hours": CACHE_TTL.total_seconds() / 3600,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "total_requests": total_requests,
        "hit_rate": round(hit_rate, 3),
        "estimated_savings_usd": round(estimated_savings, 2)
    })


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all cached responses."""
    global QUERY_CACHE, cache_hits, cache_misses
    
    cache_size_before = len(QUERY_CACHE)
    QUERY_CACHE.clear()
    
    logger.info(f"Cache cleared: {cache_size_before} entries removed")
    
    return jsonify({
        "status": "cache cleared",
        "entries_removed": cache_size_before,
        "cache_hits_reset": cache_hits,
        "cache_misses_reset": cache_misses
    })


@app.route('/api/conversation/clear', methods=['POST'])
def clear_conversation_endpoint():
    """Clear conversation history for a session."""
    data = request.json
    session_id = data.get('session_id')
    
    if session_id:
        clear_conversation(session_id)
        return jsonify({
            "status": "conversation cleared",
            "session_id": session_id
        })
    
    return jsonify({"error": "session_id required"}), 400


@app.route('/api/transcript/analyze', methods=['POST'])
def analyze_transcript():
    """Analyze transcript for course import eligibility."""
    if not client:
        return jsonify({"error": "Anthropic API key not configured"}), 500
    
    try:
        import base64
        
        transcript_text = None
        transcript_files = []
        
        # Check if file upload or text input
        if 'files' in request.files:
            # Handle multiple files
            files = request.files.getlist('files')
            if not files or files[0].filename == '':
                return jsonify({"error": "No files selected"}), 400
            
            for file in files:
                file_content = file.read()
                transcript_files.append({
                    'data': base64.b64encode(file_content).decode(),
                    'type': file.content_type or 'image/jpeg',
                    'name': file.filename
                })
            
            logger.info(f"Analyzing {len(transcript_files)} file(s): {', '.join([f['name'] for f in transcript_files])}")
            
        elif request.json and 'text' in request.json:
            transcript_text = request.json['text']
            logger.info(f"Analyzing text ({len(transcript_text)} chars)")
        else:
            return jsonify({"error": "Provide 'file' or 'text'"}), 400
        
        # Analysis prompt with comprehensive import rules
        prompt = """Analyze for Columbia CS PhD course import eligibility.

COMPLETE IMPORT RULES:
1. Grade B+ or better (REQUIRED)
2. Within past 5 years (REQUIRED)
3. Graduate course OR upper-division undergraduate (REQUIRED)
4. Must be lecture course - NOT seminar/project/reading/fieldwork (REQUIRED)
5. Listed as graduate course on official transcript (REQUIRED)
6. Full-length course granting degree credit (REQUIRED)
7. Cannot import multiple courses on same subject (REQUIRED)

STUDENT-PROVIDED FIELDS TO CHECK:
- Course Number, Name, Department
- Course Type (Lecture/Seminar/Project/Other)
- Level (Undergraduate/Graduate)
- Year Taken (YYYY)
- Semester
- Grade
- Listed as Graduate on Transcript? (Yes/No)
- Taken: Before/During Columbia PhD
- Importing Other Courses on Same Topic? (Yes/No)

ELIGIBILITY DETERMINATION:
For each course, check ALL rules above. Mark eligible ONLY if ALL required conditions met.

CRITICAL: ALL COURSES (eligible or not) MUST include these warnings showing required next steps:
- "⚠️ Requires advisor approval"
- "⚠️ Requires faculty evaluation" 
- "⚠️ Requires DGS final approval"

OUTPUT JSON FORMAT:
{
  "courses": [{
    "name": "...",
    "number": "...",
    "grade": "...",
    "year": "YYYY",
    "semester": "...",
    "level": "graduate/undergraduate upper-division/undergraduate lower-division",
    "course_type": "lecture/seminar/project/other",
    "eligible": true/false,
    "checks": {
      "grade_ok": true/false,
      "timing_ok": true/false,
      "level_ok": true/false,
      "course_type_ok": true/false,
      "on_transcript": true/false,
      "no_duplicates": true/false
    },
    "reasoning": "Detailed explanation",
    "ineligible_reasons": ["reason1", "reason2"] or [],
    "warnings": ["⚠️ Requires advisor approval", "⚠️ Requires faculty evaluation", "⚠️ Requires DGS final approval"]
  }],
  "summary": {
    "total": N,
    "eligible": N,
    "ineligible": N
  },
  "next_steps": "⚠️ IMPORTANT: All eligible courses require: 1) Advisor approval, 2) Faculty evaluation, 3) DGS final approval. Note that Columbia having an equivalent course does not automatically disqualify import, but the faculty evaluation will assess content overlap and appropriateness for your program."
}

CRITICAL: Always include the detailed next_steps message explaining the admin approval process and clarifying that Columbia equivalents don't automatically disqualify."""
        
        # Build message
        if transcript_files:
            # Add all images to content
            content = []
            for file in transcript_files:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": file['type'],
                        "data": file['data']
                    }
                })
            # Add prompt text after all images
            content.append({"type": "text", "text": prompt})
        else:
            content = f"{prompt}\n\nTRANSCRIPT:\n{transcript_text}"
        
        # Call Claude
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            temperature=0,
            messages=[{"role": "user", "content": content}]
        )
        
        result = ""
        for block in response.content:
            if hasattr(block, "text"):
                result += block.text
        
        # Parse JSON
        try:
            json_start = result.find('{')
            json_end = result.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(result[json_start:json_end])
            else:
                analysis = {"raw": result}
        except:
            analysis = {"raw": result}
        
        # Log to Google Sheets
        try:
            # Use actual transcript text as query
            query_text = transcript_text if transcript_text else "Image upload"
            
            # Format response as readable text
            if analysis.get('courses'):
                formatted_response = "ANALYSIS RESULTS\n" + "="*50 + "\n\n"
                
                for i, course in enumerate(analysis['courses'], 1):
                    status = "✓ ELIGIBLE" if course.get('eligible') else "✗ INELIGIBLE"
                    formatted_response += f"Course {i}: {course.get('name', 'Unknown')} ({course.get('number', 'N/A')}) - {status}\n"
                    formatted_response += f"  Grade: {course.get('grade', 'N/A')}, Year: {course.get('year', 'N/A')}, Department: {course.get('department', 'N/A')}\n"
                    
                    if course.get('reasoning'):
                        formatted_response += f"  Reason: {course.get('reasoning')}\n"
                    elif course.get('ineligible_reasons'):
                        formatted_response += f"  Issues: {', '.join(course.get('ineligible_reasons'))}\n"
                    
                    formatted_response += "\n"
                
                # Add summary
                if analysis.get('summary'):
                    summary = analysis['summary']
                    formatted_response += f"\nSUMMARY: {summary.get('eligible', 0)} out of {summary.get('total', 0)} courses eligible for import\n"
                
                response_text = formatted_response
            else:
                # Fallback to raw result
                response_text = result[:1000]
            
            log_to_sheets('transcript', query_text[:5000], response_text[:5000],
                         [{'name': 'transcript_analyzer'}], 1, False)
        except Exception as e:
            logger.warning(f"Failed to log transcript analysis to sheets: {e}")
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Transcript analysis error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n" + "="*60)
        print("WARNING: ANTHROPIC_API_KEY environment variable not set!")
        print("="*60)
        print("\nSet it with:")
        print("  Windows: set ANTHROPIC_API_KEY=your-key-here")
        print("  Mac/Linux: export ANTHROPIC_API_KEY=your-key-here")
        print("\nThen restart the server.")
        print("="*60 + "\n")
    
    print("\n" + "="*60)
    print("Policy Query Web App Starting...")
    print("="*60)
    
    # Initialize MCP server at startup
    print("Initializing MCP server...")
    if init_mcp_server():
        print("✓ MCP server ready")
    else:
        print("✗ MCP server failed to initialize")
        print("  Check that documents/ folder exists with policy files")
    
    # Initialize Google Sheets logging
    print("Initializing Google Sheets logging...")
    if init_google_sheets():
        print("✓ Google Sheets logging ready")
    else:
        print("✗ Google Sheets logging disabled")
    
    print(f"Open your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
