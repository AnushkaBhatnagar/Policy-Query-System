#!/usr/bin/env python3
"""
Policy Search Module
Provides search functionality for Columbia University policy documents.
"""

import json
import re
from pathlib import Path
from typing import Optional

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
