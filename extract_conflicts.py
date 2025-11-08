#!/usr/bin/env python3
"""
Conflict Extraction Script
Extracts explicit conflict annotations from policy documents.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any

class ConflictExtractor:
    def __init__(self, docs_dir: str = "documents"):
        self.docs_dir = Path(docs_dir)
        self.conflicts = []
        self.rules_db = {}  # Store all rules for reference
        
    def parse_document(self, filepath: Path) -> Dict[str, Any]:
        """Parse a single policy document and extract rules with conflicts."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract jurisdiction info from the document header
        jurisdiction_match = re.search(r'\[JURISDICTION:(\w+)\]', content)
        precedence_match = re.search(r'\[PRECEDENCE:(\d+)-(\w+)\]', content)
        
        jurisdiction = jurisdiction_match.group(1) if jurisdiction_match else "UNKNOWN"
        precedence = precedence_match.group(1) if precedence_match else "0"
        precedence_name = precedence_match.group(2) if precedence_match else "Unknown"
        
        doc_info = {
            "filepath": str(filepath),
            "jurisdiction": jurisdiction,
            "precedence": int(precedence),
            "precedence_name": precedence_name,
            "rules": []
        }
        
        # Find all RULE blocks
        rule_pattern = r'\[RULE:([^\]]+)\](.*?)(?=\[RULE:|$)'
        rules = re.finditer(rule_pattern, content, re.DOTALL)
        
        for rule_match in rules:
            rule_id = rule_match.group(1)
            rule_content = rule_match.group(2)
            
            # Extract rule metadata and conflict annotations
            rule_data = {
                "rule_id": rule_id,
                "jurisdiction": jurisdiction,
                "precedence": int(precedence),
                "content": self._extract_rule_text(rule_content),
                "conflict_notes": self._extract_tags(rule_content, 'CONFLICT-NOTE'),
                "conflict_checks": self._extract_tags(rule_content, 'CONFLICT-CHECK'),
                "see_also": self._extract_tags(rule_content, 'SEE-ALSO'),
                "override": self._extract_tags(rule_content, 'OVERRIDE'),
                "conflict_resolution": self._extract_tags(rule_content, 'CONFLICT-RESOLUTION'),
            }
            
            # Store in rules database
            self.rules_db[rule_id] = rule_data
            
            # If rule has any conflict-related annotations, add to conflicts list
            if (rule_data['conflict_notes'] or 
                rule_data['conflict_checks'] or 
                rule_data['override'] or
                rule_data['conflict_resolution'] or
                (rule_data['see_also'] and 
                 any('conflict' in tag.lower() for tag in rule_data['conflict_notes'] + rule_data['conflict_checks']))):
                
                self.conflicts.append(rule_data)
            
            doc_info["rules"].append(rule_data)
        
        return doc_info
    
    def _extract_rule_text(self, content: str) -> str:
        """Extract the main rule text, excluding metadata tags."""
        # Remove all [TAG:...] blocks
        text = re.sub(r'\[/?RULE[^\]]*\]', '', content)
        text = re.sub(r'\[[A-Z-]+:[^\]]+\]', '', text)
        text = re.sub(r'\[[A-Z-]+\]', '', text)
        return text.strip()
    
    def _extract_tags(self, content: str, tag_name: str) -> List[str]:
        """Extract all instances of a specific tag type."""
        pattern = rf'\[{tag_name}:([^\]]+)\]'
        matches = re.findall(pattern, content)
        return matches
    
    def process_all_documents(self) -> Dict[str, Any]:
        """Process all documents in the documents directory."""
        documents = []
        
        # Process each document
        for doc_file in sorted(self.docs_dir.glob("*.txt")):
            print(f"Processing {doc_file.name}...")
            doc_data = self.parse_document(doc_file)
            documents.append(doc_data)
            print(f"  Found {len(doc_data['rules'])} rules")
        
        # Organize conflicts
        organized_conflicts = self._organize_conflicts()
        
        return {
            "summary": {
                "total_documents": len(documents),
                "total_rules": len(self.rules_db),
                "total_conflicts": len(self.conflicts),
                "conflicts_by_jurisdiction": self._count_by_jurisdiction(),
            },
            "documents": documents,
            "explicit_conflicts": organized_conflicts,
        }
    
    def _organize_conflicts(self) -> List[Dict[str, Any]]:
        """Organize conflicts for easier review."""
        organized = []
        
        for conflict in self.conflicts:
            conflict_entry = {
                "rule_id": conflict["rule_id"],
                "jurisdiction": conflict["jurisdiction"],
                "precedence": conflict["precedence"],
                "conflict_indicators": {
                    "conflict_notes": conflict["conflict_notes"],
                    "conflict_checks": conflict["conflict_checks"],
                    "see_also": conflict["see_also"],
                    "override": conflict["override"],
                    "conflict_resolution": conflict["conflict_resolution"],
                },
                "rule_text_preview": conflict["content"][:200] + "..." if len(conflict["content"]) > 200 else conflict["content"]
            }
            organized.append(conflict_entry)
        
        return organized
    
    def _count_by_jurisdiction(self) -> Dict[str, int]:
        """Count conflicts by jurisdiction."""
        counts = {}
        for conflict in self.conflicts:
            jurisdiction = conflict["jurisdiction"]
            counts[jurisdiction] = counts.get(jurisdiction, 0) + 1
        return counts
    
    def save_results(self, output_file: str = "conflicts.json"):
        """Save extracted conflicts to JSON file."""
        results = self.process_all_documents()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"Results saved to {output_file}")
        print(f"{'='*60}")
        print(f"Total rules parsed: {results['summary']['total_rules']}")
        print(f"Rules with conflict annotations: {results['summary']['total_conflicts']}")
        print(f"\nConflicts by jurisdiction:")
        for jurisdiction, count in results['summary']['conflicts_by_jurisdiction'].items():
            print(f"  {jurisdiction}: {count}")
        print(f"{'='*60}")

def main():
    print("Policy Conflict Extraction Tool")
    print("="*60)
    
    extractor = ConflictExtractor()
    extractor.save_results()
    
    print("\nExtraction complete!")
    print("Review 'conflicts.json' for all extracted conflicts.")

if __name__ == "__main__":
    main()
