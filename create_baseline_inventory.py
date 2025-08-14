#!/usr/bin/env python3
"""
Enhanced Baseline Inventory Generator
Creates comprehensive artifacts for parity tracking before refactoring.
"""

import json
import re
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import ast

def find_router_prefixes(main_file: Path) -> Dict[str, str]:
    """Extract router prefixes from main.py"""
    prefixes = {}
    
    try:
        content = main_file.read_text(encoding='utf-8')
        
        # Find include_router calls with prefixes
        pattern = r'app\.include_router\(\s*(\w+)\.router\s*,\s*prefix\s*=\s*["\']([^"\']+)["\']'
        matches = re.findall(pattern, content)
        
        for router_var, prefix in matches:
            prefixes[router_var] = prefix
            
    except Exception as e:
        print(f"Warning: Could not parse router prefixes from {main_file}: {e}")
    
    return prefixes

def extract_backend_endpoints(backend_dir: Path) -> List[Dict[str, Any]]:
    """Extract all FastAPI endpoints from backend code"""
    endpoints = []
    
    # First, get router prefixes from main.py
    main_file = backend_dir / "app" / "main.py"
    router_prefixes = find_router_prefixes(main_file)
    
    # Map import names to prefixes by parsing imports
    import_to_prefix = {}
    try:
        content = main_file.read_text(encoding='utf-8')
        import_patterns = [
            r'from\s+app\.api\.endpoints\s+import\s+(\w+)\s+as\s+(\w+)',
            r'from\s+app\.api\.endpoints\.(\w+)\s+import\s+(\w+)'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if len(match) == 2:
                    module_name, var_name = match
                    if var_name in router_prefixes:
                        import_to_prefix[module_name] = router_prefixes[var_name]
    except Exception as e:
        print(f"Warning: Could not parse imports: {e}")
    
    # Search for endpoint files
    endpoints_dir = backend_dir / "app" / "api" / "endpoints"
    if not endpoints_dir.exists():
        return endpoints
    
    for endpoint_file in endpoints_dir.glob("*.py"):
        if endpoint_file.name == "__init__.py":
            continue
            
        try:
            content = endpoint_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Determine prefix for this file
            file_stem = endpoint_file.stem
            prefix = import_to_prefix.get(file_stem, "")
            
            # Extract router decorators and their paths
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Match @router.method patterns
                router_match = re.match(r'@router\.(get|post|put|delete|patch)\s*\(', line)
                if router_match:
                    method = router_match.group(1).upper()
                    
                    # Extract path from the same line or continuation
                    path = ""
                    full_decorator = line
                    
                    # Handle multi-line decorators
                    j = i
                    while j < len(lines) and not full_decorator.rstrip().endswith(')'):
                        j += 1
                        if j < len(lines):
                            full_decorator += " " + lines[j].strip()
                    
                    # Extract path from decorator
                    path_match = re.search(r'["\']([^"\']*)["\']', full_decorator)
                    if path_match:
                        path = path_match.group(1)
                        
                        # Construct full path with prefix
                        full_path = prefix + path if prefix else path
                        
                        endpoints.append({
                            "method": method,
                            "path": full_path,
                            "file": str(endpoint_file),
                            "line": i + 1,
                            "router_file": file_stem
                        })
        
        except Exception as e:
            print(f"Warning: Could not parse {endpoint_file}: {e}")
    
    return endpoints

def extract_frontend_api_calls(frontend_dir: Path) -> List[Dict[str, Any]]:
    """Extract all API calls from frontend code"""
    api_calls = []
    
    # Search for TypeScript/JavaScript files
    for file_path in frontend_dir.rglob("*.ts"):
        if file_path.name.endswith('.d.ts'):
            continue
            
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Extract apiClient calls
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                
                # Match apiClient.method patterns
                api_match = re.search(r'apiClient\.(get|post|put|delete|patch)\s*<[^>]*>\s*\(\s*[`\'"]([^`\'"]+)[`\'"]', line_stripped)
                if api_match:
                    method = api_match.group(1).upper()
                    url = api_match.group(2)
                    
                    api_calls.append({
                        "method": method,
                        "url": url,
                        "file": str(file_path),
                        "line": i + 1,
                        "type": "apiClient"
                    })
                
                # Match axios calls
                axios_match = re.search(r'axios\.(get|post|put|delete|patch)\s*\(\s*[`\'"]([^`\'"]+)[`\'"]', line_stripped)
                if axios_match:
                    method = axios_match.group(1).upper()
                    url = axios_match.group(2)
                    
                    api_calls.append({
                        "method": method,
                        "url": url,
                        "file": str(file_path),
                        "line": i + 1,
                        "type": "axios"
                    })
                
                # Match fetch calls
                fetch_match = re.search(r'fetch\s*\(\s*[`\'"]([^`\'"]+)[`\'"]', line_stripped)
                if fetch_match:
                    url = fetch_match.group(1)
                    
                    api_calls.append({
                        "method": "GET",  # Default assumption for fetch
                        "url": url,
                        "file": str(file_path),
                        "line": i + 1,
                        "type": "fetch"
                    })
        
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
    
    return api_calls

def extract_frontend_routes(frontend_dir: Path) -> List[Dict[str, Any]]:
    """Extract all frontend routes"""
    routes = []
    
    for file_path in frontend_dir.rglob("*.tsx"):
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                # Match React Router Route components
                route_match = re.search(r'<Route\s+path\s*=\s*[{"]?[\'"]([^\'\"]+)[\'"][}]?', line)
                if route_match:
                    path = route_match.group(1)
                    routes.append({
                        "path": path,
                        "file": str(file_path),
                        "line": i + 1
                    })
        
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
    
    return routes

def extract_config_variables(backend_dir: Path) -> Dict[str, Any]:
    """Extract configuration variables from backend code"""
    config = {
        "environment_variables": [],
        "settings_fields": [],
        "hardcoded_urls": [],
        "database_config": [],
        "api_keys_config": []
    }
    
    # Parse main config file
    config_file = backend_dir / "app" / "core" / "config.py"
    if config_file.exists():
        try:
            content = config_file.read_text(encoding='utf-8')
            
            # Extract field definitions from Settings class
            in_settings_class = False
            for line in content.split('\n'):
                line_stripped = line.strip()
                
                if 'class Settings' in line_stripped:
                    in_settings_class = True
                    continue
                elif in_settings_class and line_stripped.startswith('class '):
                    break
                
                if in_settings_class:
                    # Extract field definitions
                    field_match = re.match(r'(\w+):\s*([^=]+)(?:\s*=\s*(.+))?', line_stripped)
                    if field_match:
                        field_name = field_match.group(1)
                        field_type = field_match.group(2).strip()
                        default_value = field_match.group(3).strip() if field_match.group(3) else None
                        
                        # Mask sensitive values
                        if any(keyword in field_name.lower() for keyword in ['password', 'secret', 'key', 'token']):
                            if default_value and default_value not in ['None', 'null']:
                                default_value = "***MASKED***"
                        
                        field_info = {
                            "name": field_name,
                            "type": field_type,
                            "default": default_value
                        }
                        
                        # Categorize fields
                        if any(keyword in field_name.lower() for keyword in ['password', 'secret', 'key', 'passphrase']):
                            config["api_keys_config"].append(field_info)
                        elif any(keyword in field_name.lower() for keyword in ['postgres', 'database', 'db_']):
                            config["database_config"].append(field_info)
                        else:
                            config["settings_fields"].append(field_info)
        
        except Exception as e:
            print(f"Warning: Could not parse config file: {e}")
    
    # Look for hardcoded URLs in main files
    main_files = [
        backend_dir / "app" / "main.py",
        Path("oracle-trader-frontend") / "src" / "services" / "apiService.ts"
    ]
    
    for file_path in main_files:
        if file_path.exists():
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Extract URL patterns
                url_patterns = [
                    r'https?://[^\s\'"]+',
                    r'ws://[^\s\'"]+',
                    r'localhost:\d+',
                    r'127\.0\.0\.1:\d+'
                ]
                
                for pattern in url_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if match not in [item["url"] for item in config["hardcoded_urls"]]:
                            config["hardcoded_urls"].append({
                                "url": match,
                                "file": str(file_path)
                            })
            
            except Exception as e:
                print(f"Warning: Could not parse {file_path}: {e}")
    
    return config

def create_routes_inventory(frontend_routes: List[Dict[str, Any]], backend_endpoints: List[Dict[str, Any]], api_calls: List[Dict[str, Any]]) -> str:
    """Create a markdown inventory of all routes and endpoints"""
    
    md_content = """# Routes and API Inventory (Baseline)

## Frontend Routes
| Path | File | Line |
|------|------|------|
"""
    
    for route in sorted(frontend_routes, key=lambda x: x['path']):
        file_short = Path(route['file']).name
        md_content += f"| `{route['path']}` | {file_short} | {route['line']} |\n"
    
    md_content += f"\n**Total Frontend Routes:** {len(frontend_routes)}\n\n"
    
    md_content += """## Backend API Endpoints
| Method | Path | Router File | Line |
|--------|------|-------------|------|
"""
    
    for endpoint in sorted(backend_endpoints, key=lambda x: (x['method'], x['path'])):
        md_content += f"| {endpoint['method']} | `{endpoint['path']}` | {endpoint['router_file']}.py | {endpoint['line']} |\n"
    
    md_content += f"\n**Total Backend Endpoints:** {len(backend_endpoints)}\n\n"
    
    md_content += """## Frontend API Calls
| Method | URL/Path | Type | File | Line |
|--------|----------|------|------|------|
"""
    
    for call in sorted(api_calls, key=lambda x: (x['method'], x['url'])):
        file_short = Path(call['file']).name
        md_content += f"| {call['method']} | `{call['url']}` | {call['type']} | {file_short} | {call['line']} |\n"
    
    md_content += f"\n**Total API Calls:** {len(api_calls)}\n\n"
    
    # Add integration analysis
    md_content += """## Integration Analysis

### URL Matching (Frontend → Backend)
"""
    
    # Simple matching logic
    matched_calls = 0
    unmatched_calls = []
    
    for call in api_calls:
        call_url = call['url'].strip('/')
        matched = False
        
        for endpoint in backend_endpoints:
            endpoint_path = endpoint['path'].strip('/')
            
            # Simple prefix matching (ignoring parameters)
            if call_url.replace('/api/v1/', '').startswith(endpoint_path.replace('/api/v1/', '')):
                matched = True
                break
        
        if matched:
            matched_calls += 1
        else:
            unmatched_calls.append(call)
    
    md_content += f"- **Matched calls:** {matched_calls}/{len(api_calls)}\n"
    md_content += f"- **Unmatched calls:** {len(unmatched_calls)}\n"
    
    if unmatched_calls:
        md_content += "\n### Potentially Unmatched API Calls\n"
        for call in unmatched_calls[:10]:  # Show first 10
            file_short = Path(call['file']).name
            md_content += f"- `{call['method']} {call['url']}` in {file_short}:{call['line']}\n"
    
    return md_content

def main():
    """Generate baseline inventory artifacts"""
    
    repo_root = Path(".")
    backend_dir = repo_root / "oracle_trader_bot"
    frontend_dir = repo_root / "oracle-trader-frontend"
    
    print("🔍 Generating baseline parity artifacts...")
    
    # Extract backend endpoints
    print("  📡 Analyzing backend API endpoints...")
    backend_endpoints = extract_backend_endpoints(backend_dir)
    
    # Extract frontend API calls
    print("  🌐 Analyzing frontend API calls...")
    api_calls = extract_frontend_api_calls(frontend_dir)
    
    # Extract frontend routes
    print("  🛤️  Analyzing frontend routes...")
    frontend_routes = extract_frontend_routes(frontend_dir)
    
    # Extract configuration
    print("  ⚙️  Analyzing configuration variables...")
    config_info = extract_config_variables(backend_dir)
    
    # Create output directory
    os.makedirs("docs", exist_ok=True)
    
    # Write endpoints.json (replace existing)
    with open("endpoints.json", "w") as f:
        json.dump(backend_endpoints, f, indent=2)
    
    # Write api_calls.json (replace existing)
    with open("api_calls.json", "w") as f:
        json.dump(api_calls, f, indent=2)
    
    # Write routes inventory
    routes_md = create_routes_inventory(frontend_routes, backend_endpoints, api_calls)
    with open("routes_inventory.md", "w", encoding='utf-8') as f:
        f.write(routes_md)
    
    # Write config inventory
    with open("docs/config.before.md", "w", encoding='utf-8') as f:
        f.write("# Configuration Inventory (Before Refactor)\n\n")
        f.write("## Settings Fields\n")
        for field in config_info["settings_fields"]:
            f.write(f"- **{field['name']}**: `{field['type']}` = `{field['default']}`\n")
        
        f.write("\n## API Keys & Credentials\n")
        for field in config_info["api_keys_config"]:
            f.write(f"- **{field['name']}**: `{field['type']}` = `{field['default']}`\n")
        
        f.write("\n## Database Configuration\n")
        for field in config_info["database_config"]:
            f.write(f"- **{field['name']}**: `{field['type']}` = `{field['default']}`\n")
        
        f.write("\n## Hardcoded URLs Found\n")
        for url_info in config_info["hardcoded_urls"]:
            file_short = Path(url_info['file']).name
            f.write(f"- `{url_info['url']}` in {file_short}\n")
    
    # Print summary
    print("\n📊 Baseline Summary:")
    print(f"  • Backend endpoints: {len(backend_endpoints)}")
    print(f"  • Frontend API calls: {len(api_calls)}")
    print(f"  • Frontend routes: {len(frontend_routes)}")
    print(f"  • Config fields: {len(config_info['settings_fields']) + len(config_info['api_keys_config']) + len(config_info['database_config'])}")
    print(f"  • Hardcoded URLs: {len(config_info['hardcoded_urls'])}")
    
    print("\n📁 Generated Files:")
    print("  • endpoints.json")
    print("  • api_calls.json")
    print("  • routes_inventory.md")
    print("  • docs/config.before.md")
    
    # Check for uncertainties
    uncertainties = []
    
    if len(backend_endpoints) == 0:
        uncertainties.append("No backend endpoints detected - check router patterns")
    
    if len(api_calls) == 0:
        uncertainties.append("No frontend API calls detected - check client patterns")
    
    unmatched_endpoints = []
    for endpoint in backend_endpoints:
        if not endpoint['path'].startswith('/'):
            unmatched_endpoints.append(endpoint['path'])
    
    if unmatched_endpoints:
        uncertainties.append(f"Endpoints without leading slash: {unmatched_endpoints[:3]}")
    
    if uncertainties:
        print("\n⚠️  Uncertainties Found:")
        for uncertainty in uncertainties:
            print(f"  • {uncertainty}")
    else:
        print("\n✅ No major uncertainties detected")

if __name__ == "__main__":
    main()
