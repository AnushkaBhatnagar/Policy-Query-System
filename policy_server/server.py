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
            # Extract all rules with their IDs - capture content between [RULE:...] and [/RULE]
            # Allow optional whitespace (including newlines) before [/RULE]
            rule_pattern = r'\[RULE:([^\]]+)\](.*?)\s*\[/RULE\]'
            matches = re.finditer(rule_pattern, content, re.DOTALL)
            
            for match in matches:
                rule_id = match.group(1)
                rule_content = match.group(2).strip()
                
                # Clean content - remove metadata tags like [TIMING:...], [REQUIREMENT:...], etc.
                # but preserve the actual rule text
                clean_content = re.sub(r'\[/?[A-Z_-]+[^\]]*\]', '', rule_content)
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
            # Filter by department if specified (case-insensitive)
            if department and not rule_id.upper().startswith(department.upper()):
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
                'algorithm': ['algorithm', 'algorithms', 'algo'],
                'prerequisite': ['prerequisite', 'prereq', 'pre-requisite'],
                'course': ['course', 'courses', 'class', 'classes'],
            }
            
            for category, terms in keywords.items():
                if category in query_lower:
                    for term in terms:
                        if term in content_lower:
                            score += 3
            
            # Boost score if rule ID matches query keywords  
            # Extract rule ID components (e.g., "ALGO-PREREQ" from "PhD_SEAS:ALGO-PREREQ-001")
            rule_id_lower = rule_id.lower()
            rule_components = rule_id.split(':')[-1].split('-')  # Get ["ALGO", "PREREQ", "001"]
            
            for component in rule_components:
                component_lower = component.lower()
                if len(component_lower) <= 3:  # Skip numbers and very short components
                    continue
                    
                # Check if any query word is related to this component
                for word in query_words:
                    if len(word) <= 3:  # Skip very short query words
                        continue
                    
                    # Exact match or substring match
                    if component_lower in word or word in component_lower:
                        score += 20  # Very strong boost for rule ID component matches
                    # Partial match (e.g., "algo" matches "algorithm")
                    elif component_lower[:4] == word[:4] and len(word) >= 4:
                        score += 15
            
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
        """Get a specific rule by ID (case-insensitive)."""
        # Try exact match first (fastest)
        if rule_id in RULE_INDEX:
            return RULE_INDEX[rule_id]
        
        # Normalize rule_id: add RULE: prefix if missing
        normalized_id = rule_id if rule_id.startswith('RULE:') else f'RULE:{rule_id}'
        if normalized_id in RULE_INDEX:
            return RULE_INDEX[normalized_id]
        
        # Fall back to case-insensitive search with normalized ID
        normalized_id_upper = normalized_id.upper()
        for stored_id, rule_data in RULE_INDEX.items():
            if stored_id.upper() == normalized_id_upper:
                return rule_data
        
        # Also try case-insensitive search on original rule_id (in case it has unusual format)
        rule_id_upper = rule_id.upper()
        for stored_id, rule_data in RULE_INDEX.items():
            if stored_id.upper() == rule_id_upper:
                return rule_data
        
        return None
    
    def check_conflicts(self, rule_ids: list) -> list:
        """Check if any of the given rules have conflicts (case-insensitive)."""
        conflicts_found = []
        
        # Normalize input rule IDs to uppercase for comparison
        rule_ids_upper = [rid.upper() for rid in rule_ids]
        
        for conflict in self.conflicts.get('conflicts', []):
            conflict_rule_ids = [r['rule_id'] for r in conflict['rules']]
            conflict_rule_ids_upper = [rid.upper() for rid in conflict_rule_ids]
            
            # Check if any of the input rule_ids are in this conflict (case-insensitive)
            if any(rid in conflict_rule_ids_upper for rid in rule_ids_upper):
                conflicts_found.append(conflict)
        
        return conflicts_found


def load_documents():
    """Load policy documents and conflicts."""
    global DOCUMENTS, CONFLICTS
    
    docs_dir = Path(__file__).parent.parent / "documents"
    
    # Load policy documents
    for doc_file in ["gsas.txt", "isso.txt", "phd_seas.txt", "algo_prereq_signatures.txt"]:
        doc_path = docs_dir / doc_file
        if doc_path.exists():
            with open(doc_path, 'r', encoding='utf-8') as f:
                doc_name = doc_file.replace('.txt', '').upper()
                DOCUMENTS[doc_name] = f.read()
    
    # Load conflicts
    conflicts_path = Path(__file__).parent.parent / "data" / "conflicts.json"
    if conflicts_path.exists():
        with open(conflicts_path, 'r', encoding='utf-8') as f:
            CONFLICTS = json.load(f)
