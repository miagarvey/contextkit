from __future__ import annotations
import json
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path
from contextkit.schema_fp import fingerprint_schema_json
from contextkit.paths import DIRS

class SchemaDrift:
    """Detect and analyze schema changes between versions."""
    
    def __init__(self, old_schema: Dict, new_schema: Dict):
        self.old_schema = old_schema
        self.new_schema = new_schema
        self.old_fp = fingerprint_schema_json(old_schema)
        self.new_fp = fingerprint_schema_json(new_schema)
    
    def has_changes(self) -> bool:
        """Check if schemas are different."""
        return self.old_fp != self.new_fp
    
    def get_table_changes(self) -> Dict[str, str]:
        """Detect table-level changes."""
        changes = {}
        
        old_tables = set(self.old_schema.get("tables", {}).keys())
        new_tables = set(self.new_schema.get("tables", {}).keys())
        
        # New tables
        for table in new_tables - old_tables:
            changes[table] = "added"
        
        # Removed tables
        for table in old_tables - new_tables:
            changes[table] = "removed"
        
        # Modified tables
        for table in old_tables & new_tables:
            old_cols = self.old_schema["tables"][table].get("columns", {})
            new_cols = self.new_schema["tables"][table].get("columns", {})
            
            if old_cols != new_cols:
                changes[table] = "modified"
        
        return changes
    
    def get_column_changes(self, table_name: str) -> Dict[str, str]:
        """Detect column-level changes for a specific table."""
        changes = {}
        
        old_table = self.old_schema.get("tables", {}).get(table_name, {})
        new_table = self.new_schema.get("tables", {}).get(table_name, {})
        
        old_cols = set(old_table.get("columns", {}).keys())
        new_cols = set(new_table.get("columns", {}).keys())
        
        # New columns
        for col in new_cols - old_cols:
            changes[col] = "added"
        
        # Removed columns
        for col in old_cols - new_cols:
            changes[col] = "removed"
        
        # Type changes
        for col in old_cols & new_cols:
            old_type = old_table["columns"][col].get("type")
            new_type = new_table["columns"][col].get("type")
            
            if old_type != new_type:
                changes[col] = f"type_changed: {old_type} -> {new_type}"
        
        return changes
    
    def get_compatibility_level(self) -> str:
        """Assess compatibility level between schemas."""
        if not self.has_changes():
            return "identical"
        
        table_changes = self.get_table_changes()
        
        # Check if any tables were removed
        removed_tables = [t for t, change in table_changes.items() if change == "removed"]
        if removed_tables:
            return "breaking"
        
        # Check for column removals or type changes
        for table_name in self.old_schema.get("tables", {}):
            if table_name in self.new_schema.get("tables", {}):
                col_changes = self.get_column_changes(table_name)
                breaking_changes = [
                    c for c, change in col_changes.items() 
                    if change == "removed" or change.startswith("type_changed")
                ]
                if breaking_changes:
                    return "breaking"
        
        # Only additions - backward compatible
        return "compatible"
    
    def generate_migration_notes(self) -> List[str]:
        """Generate human-readable migration notes."""
        notes = []
        
        if not self.has_changes():
            return ["No schema changes detected."]
        
        table_changes = self.get_table_changes()
        
        for table, change in table_changes.items():
            if change == "added":
                notes.append(f"✅ New table: {table}")
            elif change == "removed":
                notes.append(f"❌ Removed table: {table}")
            elif change == "modified":
                col_changes = self.get_column_changes(table)
                notes.append(f"📝 Modified table: {table}")
                for col, col_change in col_changes.items():
                    if col_change == "added":
                        notes.append(f"  ✅ Added column: {col}")
                    elif col_change == "removed":
                        notes.append(f"  ❌ Removed column: {col}")
                    elif col_change.startswith("type_changed"):
                        notes.append(f"  🔄 {col}: {col_change}")
        
        return notes

def check_pack_compatibility(pack_path: Path, current_schema: Dict) -> Tuple[str, List[str]]:
    """Check if a ContextPack is compatible with current schema."""
    from contextkit.utils import load_md
    
    front, _ = load_md(pack_path)
    pack_schema_fp = front.get("schema_fingerprint")
    
    if not pack_schema_fp:
        return "unknown", ["Pack has no schema fingerprint"]
    
    current_fp = fingerprint_schema_json(current_schema)
    
    if pack_schema_fp == current_fp:
        return "identical", ["Schema fingerprints match exactly"]
    
    # Try to find the old schema file
    schema_files = list(DIRS["schema"].glob("*/*.json"))
    old_schema = None
    
    for schema_file in schema_files:
        try:
            schema_data = json.loads(schema_file.read_text())
            if fingerprint_schema_json(schema_data) == pack_schema_fp:
                old_schema = schema_data
                break
        except Exception:
            continue
    
    if not old_schema:
        return "unknown", ["Cannot find original schema file for comparison"]
    
    drift = SchemaDrift(old_schema, current_schema)
    compatibility = drift.get_compatibility_level()
    notes = drift.generate_migration_notes()
    
    return compatibility, notes

def scan_packs_for_drift(current_schema: Dict) -> Dict[str, Tuple[str, List[str]]]:
    """Scan all ContextPacks for schema compatibility."""
    results = {}
    
    for pack_file in DIRS["packs"].glob("*.md"):
        try:
            compatibility, notes = check_pack_compatibility(pack_file, current_schema)
            results[pack_file.name] = (compatibility, notes)
        except Exception as e:
            results[pack_file.name] = ("error", [f"Error checking compatibility: {e}"])
    
    return results
