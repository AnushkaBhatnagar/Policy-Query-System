#!/usr/bin/env python3
"""
MCP Policy Server
Provides tools and resources for querying Columbia University policy documents.
"""

import json
import re
from pathlib import Path
from typing import Any, Optional
import asyncio

# MCP SDK imports
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Resource,
)
import mcp.server.stdio

# Server instance
server = Server("policy-engine")

# Global data structures
DOCUMENTS = {}
CONFLICTS = {}
RULE_INDEX = {}


class PolicySearch:
    """Handles policy document searching and rule retrieval."""
    
    def __init__(self, documents: dict, conflicts: dict):
        self.documents = documents
        self.conflicts = conflicts
        self.build_rule_index()
    
    def build_rule_index(self):
        """Build index of all rules for fast lookup."""
        for doc_name, content in self.documents.items():
            # Extract all rules with their IDs
            rule_pattern = r'\[RULE:([^\]]+)\](.*?)(?=\[RULE:|$)'
            matches = re.finditer(rule_pattern, content, re.DOTALL)
            
            for match in matches:
                rule_id = match.group(1)
                rule_content = match.group(2).strip()
                
                # Clean content - remove metadata tags
                clean_content = re.sub(r'\[/?[A-Z-]+[^\]]*\]', '', rule_content)
                clean_content = clean_content.strip()
                
                RULE_INDEX[rule_id] = {
                    'id': rule_id,
                    'content': clean_content,
                    'document': doc_name,
                    'full_block': match.group(0)
                }
    
    def search(self, query: str, department: Optional[str] = None, max_results: int = 5) -> list:
        """
        Search policies using keyword matching.
        
        Args:
            query: Search query
            department: Filter by department (GSAS, ISSO, PhD_SEAS)
            max_results: Maximum number of results to return
        
        Returns:
            List of matching rules with scores
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        results = []
        
        for rule_id, rule_data in RULE_INDEX.items():
            # Filter by department if specified
            if department and not rule_id.startswith(department):
                continue
            
            content_lower = rule_data['content'].lower()
            
            # Calculate relevance score
            score = 0
            
            # Exact phrase match
            if query_lower in content_lower:
                score += 10
            
            # Word matches
            content_words = set(content_lower.split())
            matching_words = query_words & content_words
            score += len(matching_words) * 2
            
            # Keyword boosts
            keywords = {
                'defense': ['defense', 'dissertation defense'],
                'registration': ['register', 'registration', 'enroll'],
                'opt': ['opt', 'optional practical training'],
                'prospectus': ['prospectus', 'proposal'],
                'deadline': ['deadline', 'due'],
                'international': ['international', 'f-1', 'j-1', 'visa'],
            }
            
            for category, terms in keywords.items():
                if category in query_lower:
                    for term in terms:
                        if term in content_lower:
                            score += 3
            
            if score > 0:
                results.append({
                    'rule_id': rule_id,
                    'content': rule_data['content'][:300] + ('...' if len(rule_data['content']) > 300 else ''),
                    'full_content': rule_data['content'],
                    'document': rule_data['document'],
                    'score': score
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:max_results]
    
    def get_rule(self, rule_id: str) -> Optional[dict]:
        """Get a specific rule by ID."""
        return RULE_INDEX.get(rule_id)
    
    def check_conflicts(self, rule_ids: list) -> list:
        """Check if any of the given rules have conflicts."""
        conflicts_found = []
        
        for conflict in self.conflicts.get('conflicts', []):
            conflict_rule_ids = [r['rule_id'] for r in conflict['rules']]
            
            # Check if any of the input rule_ids are in this conflict
            if any(rid in conflict_rule_ids for rid in rule_ids):
                conflicts_found.append(conflict)
        
        return conflicts_found


def load_documents():
    """Load policy documents and conflicts."""
    global DOCUMENTS, CONFLICTS
    
    docs_dir = Path(__file__).parent.parent / "documents"
    
    # Load policy documents
    for doc_file in ["gsas.txt", "isso.txt", "phd_seas.txt"]:
        doc_path = docs_dir / doc_file
        if doc_path.exists():
            with open(doc_path, 'r', encoding='utf-8') as f:
                doc_name = doc_file.replace('.txt', '').upper()
                DOCUMENTS[doc_name] = f.read()
    
    # Load conflicts
    conflicts_path = Path(__file__).parent.parent / "conflicts.json"
    if conflicts_path.exists():
        with open(conflicts_path, 'r', encoding='utf-8') as f:
            CONFLICTS = json.load(f)


# Initialize search engine
policy_search = None


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_policies",
            description="Search across all policy documents for relevant rules. Returns matching rules with metadata and any known conflicts.",
            inputSchema={
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
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_rule",
            description="Get full details of a specific rule by its ID (e.g., GSAS:DEFENSE-REG-001)",
            inputSchema={
                "type": "object",
                "properties": {
                    "rule_id": {
                        "type": "string",
                        "description": "Rule ID (e.g., GSAS:DEFENSE-REG-001)"
                    }
                },
                "required": ["rule_id"]
            }
        ),
        Tool(
            name="check_conflicts",
            description="Check if given rules have any known conflicts and get precedence information",
            inputSchema={
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
        ),
        Tool(
            name="get_precedence_framework",
            description="Get the precedence hierarchy and explicit override rules",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "search_policies":
        query = arguments.get("query")
        department = arguments.get("department")
        max_results = arguments.get("max_results", 5)
        
        results = policy_search.search(query, department, max_results)
        
        # Check for conflicts among results
        result_rule_ids = [r['rule_id'] for r in results]
        conflicts = policy_search.check_conflicts(result_rule_ids)
        
        response = {
            "query": query,
            "results_count": len(results),
            "results": results,
            "conflicts_detected": len(conflicts) > 0,
            "conflicts": conflicts if conflicts else None
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
    
    elif name == "get_rule":
        rule_id = arguments.get("rule_id")
        rule = policy_search.get_rule(rule_id)
        
        if not rule:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Rule {rule_id} not found"})
            )]
        
        # Check for conflicts
        conflicts = policy_search.check_conflicts([rule_id])
        
        response = {
            "rule": rule,
            "conflicts": conflicts if conflicts else None
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
    
    elif name == "check_conflicts":
        rule_ids = arguments.get("rule_ids", [])
        conflicts = policy_search.check_conflicts(rule_ids)
        
        response = {
            "rule_ids_checked": rule_ids,
            "conflicts_found": len(conflicts),
            "conflicts": conflicts
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
    
    elif name == "get_precedence_framework":
        framework = CONFLICTS.get('precedence_framework', {})
        
        return [TextContent(
            type="text",
            text=json.dumps(framework, indent=2)
        )]
    
    return [TextContent(type="text", text=json.dumps({"error": "Unknown tool"}))]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="policy://gsas",
            name="GSAS Policy Document",
            mimeType="text/plain",
            description="Graduate School of Arts and Sciences doctoral policies"
        ),
        Resource(
            uri="policy://isso",
            name="ISSO Policy Document", 
            mimeType="text/plain",
            description="International Students and Scholars Office F-1/J-1 policies"
        ),
        Resource(
            uri="policy://phd_seas",
            name="PhD SEAS Policy Document",
            mimeType="text/plain",
            description="SEAS Computer Science PhD program policies"
        ),
        Resource(
            uri="policy://conflicts",
            name="Policy Conflicts",
            mimeType="application/json",
            description="Known conflicts between policies with precedence information"
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    
    if uri == "policy://gsas":
        return DOCUMENTS.get("GSAS", "")
    elif uri == "policy://isso":
        return DOCUMENTS.get("ISSO", "")
    elif uri == "policy://phd_seas":
        return DOCUMENTS.get("PHD_SEAS", "")
    elif uri == "policy://conflicts":
        return json.dumps(CONFLICTS, indent=2)
    
    raise ValueError(f"Unknown resource: {uri}")


async def main():
    """Run the MCP server."""
    # Load documents
    load_documents()
    
    # Initialize search engine
    global policy_search
    policy_search = PolicySearch(DOCUMENTS, CONFLICTS)
    
    # print(f"Loaded {len(DOCUMENTS)} documents", flush=True)
    # print(f"Indexed {len(RULE_INDEX)} rules", flush=True)
    # print(f"Loaded {len(CONFLICTS.get('conflicts', []))} conflicts", flush=True)
    
    # Run server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
