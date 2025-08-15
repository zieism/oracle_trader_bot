#!/usr/bin/env python3
"""
Repository Consistency Checker

Validates repository consistency rules and prevents regressions:
- No hardcoded IP addresses in source code
- No deprecated imports from shim/adapters
- Files follow naming conventions
- Exit non-zero on violations for CI integration
"""

import re
import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any
import argparse


class ConsistencyChecker:
    """Repository consistency validation"""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.violations: List[Dict[str, Any]] = []
        self.rules = self._load_rules()
    
    def _load_rules(self) -> Dict[str, Any]:
        """Load validation rules"""
        return {
            "hardcoded_ips": {
                "pattern": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
                "exclude_patterns": [
                    r"127\.0\.0\.1",  # Localhost is acceptable
                    r"0\.0\.0\.0",    # Bind-all is acceptable
                    r"203\.0\.113\.",  # RFC 5737 test addresses
                    r"192\.0\.2\.",    # RFC 5737 test addresses  
                    r"198\.51\.100\.", # RFC 5737 test addresses
                    r"10\.0\.0\.",     # RFC 1918 private addresses (test usage)
                    r"192\.168\.",     # RFC 1918 private addresses (test usage)
                    r"172\.1[6-9]\.",  # RFC 1918 private addresses part 1
                    r"172\.2[0-9]\.",  # RFC 1918 private addresses part 2
                    r"172\.3[0-1]\.",  # RFC 1918 private addresses part 3
                ],
                "exclude_files": [
                    "**/tests/**",     # Test files can have mock IPs
                    "**/test_*.py",    # Test files
                    "**/.pytest_cache/**",
                    "**/.npm/**",
                    "**/node_modules/**",
                    "**/docs/**",      # Documentation may have examples
                    "**/*.md",         # Markdown files may have examples
                    "**/reports/**",   # Reports may reference removed IPs
                    "**/*.json",       # JSON config/reports may have examples
                    "oracle_trader_bot/.runtime/**", # Runtime configuration
                    ".github_issue_*.md", # GitHub issue templates
                    "SHIM_DEPRECATION_*.md", # Deprecation documentation
                ],
                "description": "Hardcoded IP addresses (except localhost/RFC private/test IPs)"
            },
            "deprecated_imports": {
                "patterns": [
                    r"from oracle_trader_bot\.app\.",  # Only the app module shim
                    r"import oracle_trader_bot\.app\.", # Only the app module shim
                ],
                "exclude_files": [
                    "SHIM_DEPRECATION_PLAN.md",
                    "docs/**",
                    "oracle_trader_bot/__init__.py",  # Shim itself
                    "oracle_trader_bot/app/api/endpoints/__init__.py",  # Shim itself
                    "scripts/repo_consistency_check.py",  # This file defines the patterns
                    ".github_issue_*.md", # GitHub issue templates
                    "SHIM_DEPRECATION_*.md", # Deprecation documentation
                ],
                "description": "Deprecated import patterns from v1.1 shims"
            },
            "naming_conventions": {
                "python_files": {
                    "pattern": r"^[a-z_][a-z0-9_]*\.py$",
                    "paths": ["**/*.py"],
                    "exclude_paths": ["**/__pycache__/**", "**/.*/**"]
                },
                "python_dirs": {
                    "pattern": r"^[a-z_][a-z0-9_]*$",
                    "paths": ["oracle_trader_bot/**", "backend/**"],
                    "exclude_paths": ["**/__pycache__", "**/.*"]
                },
                "frontend_features": {
                    "pattern": r"^[a-z][a-z0-9-]*$",  # kebab-case
                    "paths": ["oracle-trader-frontend/src/features/*"],
                    "exclude_paths": []
                }
            }
        }
    
    def check_hardcoded_ips(self) -> int:
        """Check for hardcoded IP addresses"""
        rule = self.rules["hardcoded_ips"]
        ip_pattern = re.compile(rule["pattern"])
        exclude_patterns = [re.compile(p) for p in rule["exclude_patterns"]]
        
        violations_count = 0
        
        for file_path in self._get_source_files(rule["exclude_files"]):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        matches = ip_pattern.finditer(line)
                        for match in matches:
                            ip_address = match.group()
                            
                            # Check if this IP is in the exclude list
                            is_excluded = any(pattern.search(ip_address) for pattern in exclude_patterns)
                            if not is_excluded:
                                self.violations.append({
                                    "type": "hardcoded_ip",
                                    "file": str(file_path.relative_to(self.repo_root)),
                                    "line": line_num,
                                    "content": line.strip(),
                                    "ip": ip_address,
                                    "severity": "error"
                                })
                                violations_count += 1
                                
            except Exception as e:
                print(f"Warning: Could not read {file_path}: {e}")
        
        return violations_count
    
    def check_deprecated_imports(self) -> int:
        """Check for deprecated import patterns"""
        rule = self.rules["deprecated_imports"]
        patterns = [re.compile(p) for p in rule["patterns"]]
        
        violations_count = 0
        
        for file_path in self._get_source_files(rule["exclude_files"]):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        for pattern in patterns:
                            if pattern.search(line):
                                self.violations.append({
                                    "type": "deprecated_import",
                                    "file": str(file_path.relative_to(self.repo_root)),
                                    "line": line_num,
                                    "content": line.strip(),
                                    "pattern": pattern.pattern,
                                    "severity": "error"
                                })
                                violations_count += 1
                                break
                                
            except Exception as e:
                print(f"Warning: Could not read {file_path}: {e}")
        
        return violations_count
    
    def check_naming_conventions(self) -> int:
        """Check naming convention compliance"""
        violations_count = 0
        
        # Check Python files
        python_rule = self.rules["naming_conventions"]["python_files"]
        pattern = re.compile(python_rule["pattern"])
        
        for file_path in self.repo_root.glob("**/*.py"):
            if self._is_excluded(file_path, python_rule["exclude_paths"]):
                continue
                
            filename = file_path.name
            if not pattern.match(filename):
                self.violations.append({
                    "type": "naming_convention",
                    "subtype": "python_file",
                    "file": str(file_path.relative_to(self.repo_root)),
                    "violation": f"Filename '{filename}' should match {python_rule['pattern']}",
                    "severity": "warning"
                })
                violations_count += 1
        
        # Check directory names
        for rule_name, rule in self.rules["naming_conventions"].items():
            if rule_name == "python_files":
                continue
                
            for glob_pattern in rule["paths"]:
                for path in self.repo_root.glob(glob_pattern):
                    if path.is_dir() and not self._is_excluded(path, rule["exclude_paths"]):
                        dirname = path.name
                        pattern = re.compile(rule["pattern"])
                        if not pattern.match(dirname):
                            self.violations.append({
                                "type": "naming_convention",
                                "subtype": rule_name,
                                "file": str(path.relative_to(self.repo_root)),
                                "violation": f"Directory '{dirname}' should match {rule['pattern']}",
                                "severity": "warning"
                            })
                            violations_count += 1
        
        return violations_count
    
    def _get_source_files(self, exclude_files: List[str]) -> List[Path]:
        """Get all source files, excluding specified patterns"""
        source_extensions = ['.py', '.ts', '.tsx', '.js', '.jsx', '.md', '.yml', '.yaml', '.json']
        exclude_patterns = [Path(self.repo_root / pattern.replace('**/', '')) for pattern in exclude_files]
        
        source_files = []
        for ext in source_extensions:
            for file_path in self.repo_root.glob(f"**/*{ext}"):
                if not self._is_excluded(file_path, exclude_files):
                    source_files.append(file_path)
        
        return source_files
    
    def _is_excluded(self, file_path: Path, exclude_patterns: List[str]) -> bool:
        """Check if file matches any exclude pattern"""
        relative_path = file_path.relative_to(self.repo_root)
        path_str = str(relative_path).replace('\\', '/')
        
        for pattern in exclude_patterns:
            # Simple glob-like matching
            if '*' in pattern:
                pattern_regex = pattern.replace('**/', '.*').replace('*', '[^/]*')
                if re.match(pattern_regex, path_str):
                    return True
            else:
                if pattern in path_str:
                    return True
        
        return False
    
    def run_all_checks(self) -> Dict[str, int]:
        """Run all consistency checks"""
        print("🔍 Running repository consistency checks...")
        
        results = {
            "hardcoded_ips": self.check_hardcoded_ips(),
            "deprecated_imports": self.check_deprecated_imports(),
            "naming_conventions": self.check_naming_conventions()
        }
        
        return results
    
    def print_results(self, results: Dict[str, int]) -> int:
        """Print results and return exit code"""
        total_violations = sum(results.values())
        
        if total_violations == 0:
            print("✅ All consistency checks passed!")
            return 0
        
        print(f"\n❌ Found {total_violations} violations:\n")
        
        # Group violations by type
        by_type = {}
        for violation in self.violations:
            v_type = violation["type"]
            if v_type not in by_type:
                by_type[v_type] = []
            by_type[v_type].append(violation)
        
        # Print violations
        for v_type, violations in by_type.items():
            print(f"🚨 {v_type.upper().replace('_', ' ')} ({len(violations)} violations):")
            for v in violations[:10]:  # Limit output
                severity = v.get("severity", "error")
                print(f"  [{severity.upper()}] {v['file']}:{v.get('line', '?')}")
                if "content" in v:
                    print(f"    {v['content']}")
                elif "violation" in v:
                    print(f"    {v['violation']}")
                print()
            
            if len(violations) > 10:
                print(f"    ... and {len(violations) - 10} more violations\n")
        
        return 1 if total_violations > 0 else 0


def main():
    parser = argparse.ArgumentParser(description="Repository consistency checker")
    parser.add_argument("--repo-root", default=".", help="Repository root directory")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--strict", action="store_true", help="Strict mode - fail on documentation violations")
    
    args = parser.parse_args()
    
    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        print(f"Error: Repository root {repo_root} does not exist")
        return 2
    
    checker = ConsistencyChecker(repo_root)
    results = checker.run_all_checks()
    
    # Filter out documentation violations in non-strict mode
    if not args.strict:
        doc_patterns = ["docs/", "reports/", ".md", ".json"]
        original_count = len(checker.violations)
        checker.violations = [
            v for v in checker.violations 
            if not any(pattern in v.get("file", "") for pattern in doc_patterns)
            or v["type"] != "hardcoded_ip"
        ]
        filtered_count = original_count - len(checker.violations)
        if filtered_count > 0 and args.verbose:
            print(f"📝 Filtered {filtered_count} documentation-only violations (use --strict to include them)")
        
        # Recalculate results
        results = {
            "hardcoded_ips": sum(1 for v in checker.violations if v["type"] == "hardcoded_ip"),
            "deprecated_imports": sum(1 for v in checker.violations if v["type"] == "deprecated_import"), 
            "naming_conventions": sum(1 for v in checker.violations if v["type"] == "naming_convention")
        }
    
    if args.json:
        output = {
            "results": results,
            "violations": checker.violations,
            "total_violations": sum(results.values())
        }
        print(json.dumps(output, indent=2))
        return 0
    else:
        return checker.print_results(results)


if __name__ == "__main__":
    sys.exit(main())
