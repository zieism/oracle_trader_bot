#!/usr/bin/env python3
"""
Unified Import Rewriter

This script coordinates both backend (Python) and frontend (TypeScript/JavaScript) 
import rewriting to prepare for the structural refactoring.

Usage:
    python scripts/rewrite_all_imports.py [--dry-run] [--verbose] [--backend-only] [--frontend-only]

Options:
    --dry-run         Show what would be changed without making modifications
    --verbose         Show detailed information about changes
    --backend-only    Only rewrite backend Python imports
    --frontend-only   Only rewrite frontend TypeScript/JavaScript imports
"""

import argparse
import subprocess
import sys
from pathlib import Path

def run_command(cmd: list, description: str, verbose: bool = False) -> bool:
    """
    Run a command and return success status.
    """
    if verbose:
        print(f"🔧 Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            if verbose or result.stdout.strip():
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} failed:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        print(f"Make sure the required dependencies are installed.")
        return False
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False

def main():
    """Main entry point for the unified import rewriter."""
    parser = argparse.ArgumentParser(
        description="Rewrite imports for both backend and frontend"
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
        '--backend-only',
        action='store_true',
        help='Only rewrite backend Python imports'
    )
    parser.add_argument(
        '--frontend-only', 
        action='store_true',
        help='Only rewrite frontend TypeScript/JavaScript imports'
    )
    
    args = parser.parse_args()
    
    # Determine which rewriters to run
    run_backend = not args.frontend_only
    run_frontend = not args.backend_only
    
    success = True
    
    print("🚀 Starting unified import rewriting...")
    
    if run_backend:
        print("\n" + "="*60)
        print("🐍 BACKEND IMPORT REWRITING")
        print("="*60)
        
        backend_cmd = [
            sys.executable, 
            'scripts/rewrite_backend_imports.py',
            '--path', '.'
        ]
        
        if args.dry_run:
            backend_cmd.append('--dry-run')
        if args.verbose:
            backend_cmd.append('--verbose')
            
        backend_success = run_command(
            backend_cmd,
            "Backend import rewriting",
            verbose=args.verbose
        )
        
        if not backend_success:
            success = False
            print("⚠️  Backend import rewriting encountered issues")
    
    if run_frontend:
        print("\n" + "="*60)
        print("🌐 FRONTEND IMPORT REWRITING") 
        print("="*60)
        
        frontend_cmd = [
            'node',
            'scripts/rewrite_frontend_imports.js'
        ]
        
        if args.dry_run:
            frontend_cmd.append('--dry-run')
        if args.verbose:
            frontend_cmd.append('--verbose')
            
        frontend_success = run_command(
            frontend_cmd,
            "Frontend import rewriting", 
            verbose=args.verbose
        )
        
        if not frontend_success:
            success = False
            print("⚠️  Frontend import rewriting encountered issues")
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    if success:
        action = "prepared" if args.dry_run else "completed"
        print(f"✅ Import rewriting {action} successfully!")
        
        if args.dry_run:
            print("\n💡 Run without --dry-run to apply all changes")
        else:
            print("\n🎉 All imports have been updated for the new structure!")
            print("You can now proceed with moving files to their new locations.")
    else:
        print("❌ Some import rewriting operations failed.")
        print("Please check the error messages above and resolve any issues.")
        sys.exit(1)

if __name__ == '__main__':
    main()
