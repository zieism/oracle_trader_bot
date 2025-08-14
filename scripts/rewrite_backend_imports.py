#!/usr/bin/env python3
"""
Backend Import Rewriter

This script safely updates import statements across the backend codebase
to use the new router-based structure. It uses AST parsing to ensure
safe and accurate replacements.

Usage:
    python scripts/rewrite_backend_imports.py [--dry-run] [--verbose]
    
Options:
    --dry-run    Show what would be changed without making modifications
    --verbose    Show detailed information about changes
"""

import ast
import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

# Import mapping from old paths to new paths - Phase 2 specific mappings
BACKEND_IMPORT_MAPPING = {
    # Services (Phase 2 moves)
    'app.services.position_monitor': 'app.services.position_monitor',
    'app.exchange_clients.kucoin_futures_client': 'app.services.kucoin_futures_client',
    
    # Strategies (Phase 2 moves)
    'app.strategies.trend_following_strategy': 'app.strategies.trend_following_strategy',
    'app.strategies.range_trading_strategy': 'app.strategies.range_trading_strategy',
    
    # Indicators (Phase 2 moves)
    'app.indicators.technical_indicators': 'app.indicators.technical_indicators',
    
    # Analysis service (Phase 2 reorganization)
    'app.analysis.market_regime': 'app.services.market_regime_service',
    
    # Keep existing core and API mappings intact (these will be handled in future phases)
    'app.core.config': 'app.core.config',
    'app.api.dependencies': 'app.api.dependencies',
    'app.db': 'app.db',
    'app.models': 'app.models',
    'app.schemas': 'app.schemas', 
    'app.crud': 'app.crud',
}

# Alias mapping for imports that need to be renamed in merged files
IMPORT_ALIAS_MAPPING = {
    # When merging endpoints, some imports may need aliases
    'bot_settings_api': 'settings_router',
    'bot_management_api': 'management_router',
    'order_management': 'orders_router',
    'exchange_info': 'exchange_router',
    'market_data': 'market_router',
    'server_logs_api': 'logs_router',
    'frontend_fastui': 'ui_router',
}

class ImportRewriter(ast.NodeTransformer):
    """
    AST transformer that rewrites import statements.
    """
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.changes = []
        
    def visit_Import(self, node: ast.Import) -> ast.Import:
        """Handle 'import module' statements."""
        modified = False
        new_names = []
        
        for alias in node.names:
            old_name = alias.name
            new_name = BACKEND_IMPORT_MAPPING.get(old_name)
            
            if new_name:
                if self.verbose:
                    self.changes.append(f"Import: {old_name} → {new_name}")
                
                # Create new alias if needed
                new_alias = ast.alias(name=new_name, asname=alias.asname)
                new_names.append(new_alias)
                modified = True
            else:
                new_names.append(alias)
        
        if modified:
            node.names = new_names
            
        return node
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        """Handle 'from module import ...' statements."""
        if not node.module:
            return node
            
        old_module = node.module
        new_module = BACKEND_IMPORT_MAPPING.get(old_module)
        
        if new_module:
            if self.verbose:
                imports = ', '.join([alias.name for alias in node.names])
                self.changes.append(f"From import: from {old_module} import {imports} → from {new_module} import {imports}")
            
            node.module = new_module
            
            # Handle potential alias updates for merged modules
            new_names = []
            for alias in node.names:
                old_name = alias.name
                new_alias_name = IMPORT_ALIAS_MAPPING.get(old_name)
                
                if new_alias_name and not alias.asname:
                    # Add alias for renamed imports
                    new_alias = ast.alias(name=old_name, asname=new_alias_name)
                    new_names.append(new_alias)
                else:
                    new_names.append(alias)
            
            node.names = new_names
        
        return node

def rewrite_file_imports(file_path: Path, dry_run: bool = False, verbose: bool = False) -> bool:
    """
    Rewrite imports in a single Python file.
    
    Returns:
        bool: True if changes were made, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        # Apply transformations
        rewriter = ImportRewriter(dry_run=dry_run, verbose=verbose)
        new_tree = rewriter.visit(tree)
        
        if rewriter.changes:
            if verbose:
                print(f"\n📝 Changes for {file_path}:")
                for change in rewriter.changes:
                    print(f"  • {change}")
            
            if not dry_run:
                # Convert back to source code
                import astor
                new_content = astor.to_source(new_tree)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                    
            return True
        
        return False
        
    except SyntaxError as e:
        print(f"⚠️  Syntax error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Error processing {file_path}: {e}")
        return False

def find_python_files(root_path: Path) -> List[Path]:
    """Find all Python files in the given path."""
    python_files = []
    
    for pattern in ['**/*.py']:
        python_files.extend(root_path.glob(pattern))
    
    # Filter out __pycache__ and other unwanted directories
    filtered_files = []
    for file_path in python_files:
        if '__pycache__' not in str(file_path) and '.git' not in str(file_path):
            filtered_files.append(file_path)
    
    return filtered_files

def main():
    """Main entry point for the import rewriter."""
    parser = argparse.ArgumentParser(
        description="Rewrite backend imports for the new router-based structure"
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be changed without making modifications'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true', 
        help='Show detailed information about changes'
    )
    parser.add_argument(
        '--path',
        type=str,
        default='.',
        help='Root path to search for Python files (default: current directory)'
    )
    
    args = parser.parse_args()
    
    root_path = Path(args.path).resolve()
    
    if not root_path.exists():
        print(f"❌ Path does not exist: {root_path}")
        sys.exit(1)
    
    print(f"🔍 Searching for Python files in: {root_path}")
    python_files = find_python_files(root_path)
    
    if not python_files:
        print("❌ No Python files found")
        sys.exit(1)
    
    print(f"📁 Found {len(python_files)} Python files")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
    
    changed_files = 0
    
    for file_path in python_files:
        if rewrite_file_imports(file_path, dry_run=args.dry_run, verbose=args.verbose):
            changed_files += 1
            if not args.verbose:
                print(f"✏️  Modified: {file_path}")
    
    if changed_files:
        action = "would be modified" if args.dry_run else "modified"
        print(f"\n✅ {changed_files} files {action}")
    else:
        print(f"\n✅ No import changes needed")
    
    if args.dry_run and changed_files:
        print("\n💡 Run without --dry-run to apply changes")

if __name__ == '__main__':
    main()
