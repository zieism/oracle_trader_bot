#!/usr/bin/env python3
"""
Phase 2 Import Rewriter

This script specifically updates import statements for the Phase 2 structural moves:
- Services: position_monitor, kucoin_futures_client, market_regime_service
- Strategies: trend_following_strategy, range_trading_strategy  
- Indicators: technical_indicators

Usage:
    python scripts/rewrite_phase2_imports.py [--dry-run] [--verbose]
"""

import ast
import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

# Phase 2 specific import mappings - only the moves we made
PHASE2_IMPORT_MAPPING = {
    # Exchange client moved to services
    'app.exchange_clients.kucoin_futures_client': 'app.services.kucoin_futures_client',
    'oracle_trader_bot.app.exchange_clients.kucoin_futures_client': 'backend.app.services.kucoin_futures_client',
    
    # Market regime analysis moved to services
    'app.analysis.market_regime': 'app.services.market_regime_service',
    'oracle_trader_bot.app.analysis.market_regime': 'backend.app.services.market_regime_service',
    
    # Services remain in services (just path updates)
    'oracle_trader_bot.app.services.position_monitor': 'backend.app.services.position_monitor',
    
    # Strategies path updates
    'oracle_trader_bot.app.strategies.trend_following_strategy': 'backend.app.strategies.trend_following_strategy',
    'oracle_trader_bot.app.strategies.range_trading_strategy': 'backend.app.strategies.range_trading_strategy',
    
    # Indicators path updates
    'oracle_trader_bot.app.indicators.technical_indicators': 'backend.app.indicators.technical_indicators',
}

# Files that need import updates for Phase 2
PHASE2_TARGET_FILES = [
    # Backend files (new structure)
    'backend/app/services/position_monitor.py',
    'backend/app/services/kucoin_futures_client.py', 
    'backend/app/services/market_regime_service.py',
    'backend/app/strategies/trend_following_strategy.py',
    'backend/app/strategies/range_trading_strategy.py',
    'backend/app/indicators/technical_indicators.py',
    'backend/app/main.py',
    
    # Original files that might import moved modules
    'oracle_trader_bot/app/main.py',
    'oracle_trader_bot/bot_engine.py',
    'run_server.py',
]

class ImportRewriter(ast.NodeTransformer):
    """AST node transformer that rewrites import statements."""
    
    def __init__(self, verbose: bool = False):
        self.changes: List[str] = []
        self.verbose = verbose
    
    def visit_Import(self, node: ast.Import) -> ast.Import:
        """Handle 'import module' statements."""
        changed = False
        new_aliases = []
        
        for alias in node.names:
            old_name = alias.name
            new_name = self._map_import_name(old_name)
            
            if new_name != old_name:
                changed = True
                self.changes.append(f"import {old_name} → import {new_name}")
                alias.name = new_name
            
            new_aliases.append(alias)
        
        if changed:
            node.names = new_aliases
        
        return node
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        """Handle 'from module import ...' statements."""
        if node.module is None:
            return node
            
        old_module = node.module
        new_module = self._map_import_name(old_module)
        
        if new_module != old_module:
            self.changes.append(f"from {old_module} → from {new_module}")
            node.module = new_module
        
        return node
    
    def _map_import_name(self, name: str) -> str:
        """Map an import name using the PHASE2_IMPORT_MAPPING."""
        # Direct mapping
        if name in PHASE2_IMPORT_MAPPING:
            return PHASE2_IMPORT_MAPPING[name]
        
        # Check for partial matches (submodules)
        for old_prefix, new_prefix in PHASE2_IMPORT_MAPPING.items():
            if name.startswith(old_prefix + '.'):
                # Replace the prefix
                return new_prefix + name[len(old_prefix):]
        
        return name

def rewrite_file_imports(file_path: Path, dry_run: bool = False, verbose: bool = False) -> bool:
    """Rewrite imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Parse the AST
        try:
            tree = ast.parse(original_content, filename=str(file_path))
        except SyntaxError as e:
            if verbose:
                print(f"⚠️  Skipping {file_path}: Syntax error - {e}")
            return False
        
        # Transform imports
        rewriter = ImportRewriter(verbose=verbose)
        new_tree = rewriter.visit(tree)
        
        if not rewriter.changes:
            if verbose:
                print(f"✅ {file_path}: No changes needed")
            return False
        
        if verbose or dry_run:
            print(f"\n📝 {file_path}:")
            for change in rewriter.changes:
                print(f"    {change}")
        
        if not dry_run:
            # Convert AST back to source code
            import astor
            new_content = astor.to_source(new_tree)
            
            # Write the updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main entry point for the Phase 2 import rewriter."""
    parser = argparse.ArgumentParser(
        description="Rewrite Phase 2 imports for services/strategies/indicators moves"
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
    
    args = parser.parse_args()
    
    print("🔄 Phase 2 Import Rewriter - Services/Strategies/Indicators")
    print("=" * 60)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
    
    # Check which target files exist
    existing_files = []
    missing_files = []
    
    for file_path in PHASE2_TARGET_FILES:
        full_path = Path(file_path)
        if full_path.exists():
            existing_files.append(full_path)
        else:
            missing_files.append(file_path)
    
    print(f"📁 Found {len(existing_files)} target files")
    if missing_files and args.verbose:
        print(f"⚠️  Missing files (will skip): {', '.join(missing_files)}")
    
    changed_files = 0
    
    for file_path in existing_files:
        try:
            if rewrite_file_imports(file_path, dry_run=args.dry_run, verbose=args.verbose):
                changed_files += 1
                if not args.verbose and not args.dry_run:
                    print(f"✏️  Modified: {file_path}")
        except Exception as e:
            print(f"❌ Failed to process {file_path}: {e}")
    
    print("\n" + "=" * 60)
    if changed_files:
        action = "would be modified" if args.dry_run else "modified"
        print(f"✅ {changed_files} files {action}")
    else:
        print("✅ No import changes needed")
    
    if args.dry_run and changed_files:
        print("\n💡 Run without --dry-run to apply changes")

if __name__ == '__main__':
    main()
