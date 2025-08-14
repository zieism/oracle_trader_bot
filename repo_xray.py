# repo_xray.py
import os, re, json, ast, sys
import requests
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

ROOT = Path(__file__).parent

PY_PATTERNS = (".py",)
FE_PATTERNS = (".ts", ".tsx", ".js", ".jsx")

# ---------- Utilities ----------
def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def walk_files(root: Path, exts: Tuple[str, ...]) -> List[Path]:
    files = []
    for dp, _, fnames in os.walk(root):
        for fn in fnames:
            if fn.endswith(exts):
                files.append(Path(dp) / fn)
    return files

# ---------- Python analysis ----------
class PyImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports: List[str] = []
    def visit_Import(self, node: ast.Import):
        for n in node.names:
            self.imports.append(n.name)
    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.append(node.module)

FASTAPI_METHODS = {"get","post","put","patch","delete","options","head"}

class FastAPIFinder(ast.NodeVisitor):
    def __init__(self):
        self.apps: List[str] = []           # FastAPI() instances
        self.routers: Dict[str, Dict[str, Any]] = {}  # name -> {"prefix":..., "routes":[...]}
        self.routes: List[Dict[str, Any]] = []        # flat list of routes
        self.models: Dict[str, Dict[str, Any]] = {}   # class -> {"bases":[...], "fields":[(name,annotation)]}
        self.seen_names: Dict[str, str] = {}          # var -> type name (FastAPI/APIRouter)
    def visit_Assign(self, node: ast.Assign):
        # Detect FastAPI()/APIRouter()
        try:
            val = node.value
            target_names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name):
                fname = val.func.id
                if fname == "FastAPI":
                    for tn in target_names:
                        self.seen_names[tn] = "FastAPI"
                        self.apps.append(tn)
                if fname == "APIRouter":
                    prefix = None
                    for kw in val.keywords or []:
                        if kw.arg == "prefix":
                            if isinstance(kw.value, ast.Constant):
                                prefix = kw.value.value
                    for tn in target_names:
                        self.seen_names[tn] = "APIRouter"
                        self.routers[tn] = {"prefix": prefix or "", "routes": []}
        except Exception:
            pass
        self.generic_visit(node)
    def visit_ClassDef(self, node: ast.ClassDef):
        # Pydantic/SQLAlchemy models
        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(f"{getattr(b.value,'id',None)}.{b.attr}")
        fields = []
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                name = stmt.target.id
                ann = getattr(stmt.annotation, 'id', None) or getattr(getattr(stmt.annotation,'attr',None),'',None)
                fields.append((name, ann or ast.unparse(stmt.annotation) if hasattr(ast,"unparse") else ""))
        self.models[node.name] = {"bases": bases, "fields": fields}
        self.generic_visit(node)
    def visit_Call(self, node: ast.Call):
        # router.get("/path") decorators are actually found in FunctionDef decorators.
        self.generic_visit(node)
    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Look for @router.get("/x") or @app.post("/y")
        for dec in node.decorator_list:
            try:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    attr = dec.func.attr  # get/post/put...
                    if attr in FASTAPI_METHODS:
                        obj = dec.func.value  # router / app
                        obj_name = None
                        if isinstance(obj, ast.Name):
                            obj_name = obj.id
                        path_val = ""
                        if dec.args:
                            arg0 = dec.args[0]
                            if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                                path_val = arg0.value
                        route = {
                            "method": attr.upper(),
                            "path": path_val,
                            "func": node.name,
                            "on": obj_name
                        }
                        self.routes.append(route)
                        if obj_name in self.routers:
                            self.routers[obj_name]["routes"].append(route)
            except Exception:
                pass
        self.generic_visit(node)

def analyze_python(files: List[Path]) -> Dict[str, Any]:
    graph = {}    # file -> list(imports)
    fastapi = {"apps": [], "routers": {}, "routes": [], "models": {}}
    kucoin_hits = []

    for f in files:
        src = read_text(f)
        try:
            tree = ast.parse(src)
        except Exception:
            continue
        iv = PyImportVisitor()
        iv.visit(tree)
        graph[str(f)] = iv.imports

        fv = FastAPIFinder()
        fv.visit(tree)

        if fv.apps:
            fastapi["apps"].extend([{"file": str(f), "var": a} for a in fv.apps])
        for k,v in fv.routers.items():
            v2 = dict(v)
            v2["file"] = str(f)
            fastapi["routers"][f"{k}@{f}"] = v2
        if fv.routes:
            for r in fv.routes:
                r2 = dict(r)
                r2["file"] = str(f)
                # prefix merge: if router has a prefix, join it
                if r2.get("on"):
                    for rid, R in fastapi["routers"].items():
                        if rid.startswith(r2["on"]+"@") and R.get("file")==str(f):
                            pfx = R.get("prefix","") or ""
                            if pfx and r2["path"]:
                                # avoid '//' duplicates
                                r2["full_path"] = (pfx.rstrip("/") + "/" + r2["path"].lstrip("/")).replace("//","/")
                            else:
                                r2["full_path"] = r2["path"] or pfx or ""
                fastapi["routes"].append(r2)

        # Quick KuCoin/ccxt sniff
        if any(k in src for k in ("ccxt", "kucoinfutures", "kucoin", "KucoinFuturesClient", "create_futures_order")):
            kucoin_hits.append(str(f))

        # models
        for name, meta in fv.models.items():
            base_str = " ".join(meta["bases"])
            if any(b in base_str for b in ("BaseModel","DeclarativeMeta","Base")):
                fastapi["models"][f"{name}@{f}"] = meta

    return {"imports": graph, "fastapi": fastapi, "kucoin_files": kucoin_hits}

# ---------- Frontend analysis ----------
FETCH_RE = re.compile(r'\bfetch\s*\(\s*([\'"])(?P<url>.+?)\1', re.I)
AXIOS_RE = re.compile(r'\baxios\s*\.\s*(get|post|put|patch|delete)\s*\(\s*([\'"])(?P<url>.+?)\2', re.I)
ROUTE_RE_6 = re.compile(r'<Route\s+path\s*=\s*{?["\'](?P<path>[^"\'}]+)["\']}?', re.I)
ROUTE_OBJ = re.compile(r'path\s*:\s*["\'](?P<path>[^"\']+)["\']', re.I)

def analyze_frontend(files: List[Path]) -> Dict[str, Any]:
    api_calls = []   # {file, type, method?, url, line}
    routes = []      # {file, path, line}
    for f in files:
        src = read_text(f)
        if not src:
            continue
        # fetch calls
        for m in FETCH_RE.finditer(src):
            url = m.group("url")
            line = src[:m.start()].count("\n") + 1
            api_calls.append({"file": str(f), "lib": "fetch", "method": "GET(assumed)", "url": url, "line": line})
        # axios calls
        for m in AXIOS_RE.finditer(src):
            url = m.group("url")
            method = src[m.start():m.end()].split("axios.")[1].split("(")[0]
            line = src[:m.start()].count("\n") + 1
            api_calls.append({"file": str(f), "lib": "axios", "method": method.upper(), "url": url, "line": line})
        # react-router jsx
        for m in ROUTE_RE_6.finditer(src):
            path = m.group("path")
            line = src[:m.start()].count("\n") + 1
            routes.append({"file": str(f), "path": path, "line": line})
        # route objects (array of routes)
        for m in ROUTE_OBJ.finditer(src):
            path = m.group("path")
            routes.append({"file": str(f), "path": path})
    return {"api_calls": api_calls, "routes": routes}

# ---------- Live OpenAPI Analysis ----------
def fetch_live_openapi(base_url: str = "http://localhost:8000") -> Optional[Dict[str, Any]]:
    """Fetch OpenAPI spec from running server"""
    try:
        openapi_url = f"{base_url}/openapi.json"
        response = requests.get(openapi_url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Could not fetch live OpenAPI from {base_url}/openapi.json: {e}")
    return None

def parse_openapi_endpoints(openapi_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse OpenAPI spec and extract endpoints"""
    endpoints = []
    paths = openapi_spec.get("paths", {})
    
    for path, methods in paths.items():
        for method, spec in methods.items():
            if method.lower() in {"get", "post", "put", "patch", "delete", "options", "head"}:
                endpoint = {
                    "method": method.upper(),
                    "path": path,
                    "full_path": path,
                    "func": spec.get("operationId", "unknown"),
                    "on": "live_api",
                    "file": "live_server",
                    "summary": spec.get("summary", ""),
                    "tags": spec.get("tags", []),
                    "source": "live_openapi"
                }
                endpoints.append(endpoint)
    
    return endpoints

def merge_endpoints(static_endpoints: List[Dict[str, Any]], live_endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge static and live endpoints, deduplicating by method+path"""
    merged = []
    seen_keys = set()
    
    # Add static endpoints first
    for ep in static_endpoints:
        key = (ep["method"], ep.get("full_path") or ep.get("path", ""))
        if key not in seen_keys:
            ep_copy = dict(ep)
            ep_copy["source"] = "static_scan"
            merged.append(ep_copy)
            seen_keys.add(key)
    
    # Add live endpoints that aren't duplicates
    live_only = []
    for ep in live_endpoints:
        key = (ep["method"], ep.get("full_path") or ep.get("path", ""))
        if key not in seen_keys:
            merged.append(ep)
            live_only.append(ep)
            seen_keys.add(key)
    
    return {
        "merged_endpoints": merged,
        "live_only_endpoints": live_only,
        "static_count": len(static_endpoints),
        "live_count": len(live_endpoints),
        "merged_count": len(merged),
        "live_only_count": len(live_only)
    }
def normalize_url(u: str) -> str:
    # remove base url, keep path; crude heuristic
    u = re.sub(r'^https?://[^/]+', '', u)
    return u

def match_calls_to_endpoints(api_calls: List[Dict[str,Any]], endpoints: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    matches = []
    for call in api_calls:
        p = normalize_url(call["url"])
        best = []
        for ep in endpoints:
            ep_path = ep.get("full_path") or ep.get("path") or ""
            if not ep_path:
                continue
            if p.split("?")[0].rstrip("/") == ep_path.rstrip("/"):
                best.append(ep)
        matches.append({"call": call, "matches": best})
    return matches

# ---------- Report ----------
def write_json(name: str, data: Any):
    Path(name).write_text(json.dumps(data, indent=2), encoding="utf-8")

def write_report(py_res: Dict[str,Any], fe_res: Dict[str,Any], matches: List[Dict[str,Any]], openapi_result: Optional[Dict[str,Any]] = None):
    lines = []
    lines.append("# Repository X-Ray Report\n")
    
    # OpenAPI Live Analysis Section
    if openapi_result:
        lines.append("## Live OpenAPI Analysis\n")
        lines.append(f"- Static scan found: {openapi_result['static_count']} endpoints")
        lines.append(f"- Live server found: {openapi_result['live_count']} endpoints") 
        lines.append(f"- Merged total (deduplicated): {openapi_result['merged_count']} endpoints")
        if openapi_result['live_only_count'] > 0:
            lines.append(f"- **Live-only endpoints**: {openapi_result['live_only_count']} (not detected in static scan)")
            lines.append("\n### Live-Only Endpoints\n")
            for ep in openapi_result['live_only_endpoints']:
                tags = f" ({', '.join(ep['tags'])})" if ep.get('tags') else ""
                lines.append(f"- [{ep['method']}] `{ep['path']}`{tags} - {ep.get('summary', '')}")
        lines.append(f"\n_Full live analysis saved to: reports/openapi_live.json_\n")
    
    # FastAPI
    fa = py_res["fastapi"]
    lines.append("## Backend (from code)\n")
    if fa["apps"]:
        lines.append(f"- FastAPI apps: {len(fa['apps'])}")
        for a in fa["apps"]:
            lines.append(f"  - app var `{a['var']}` in `{a['file']}`")
    lines.append(f"- Routers detected: {len(fa['routers'])}")
    lines.append(f"- Endpoints detected: {len(fa['routes'])}\n")
    if fa["routes"]:
        lines.append("### Endpoints\n")
        for r in sorted(fa["routes"], key=lambda x: (x.get("full_path") or x.get("path") or "", x["method"])):
            lines.append(f"- [{r['method']}] `{r.get('full_path') or r.get('path')}` → `{r['func']}()` ({r['file']})")
    if fa["models"]:
        lines.append("\n### Data Models (Pydantic/SQLAlchemy guess)\n")
        for k, m in fa["models"].items():
            base = ", ".join(m["bases"])
            lines.append(f"- `{k}` bases: {base}")
    if py_res["kucoin_files"]:
        lines.append("\n### KuCoin/ccxt usage (files)\n")
        for f in py_res["kucoin_files"]:
            lines.append(f"- {f}")

    # Frontend
    lines.append("\n## Frontend (from code)\n")
    lines.append(f"- Routes detected: {len(fe_res['routes'])}")
    for r in fe_res["routes"]:
        lines.append(f"  - `{r['path']}` ({r['file']})")
    lines.append(f"- API calls detected: {len(fe_res['api_calls'])}")
    for c in fe_res["api_calls"]:
        lines.append(f"  - {c['lib']} {c['method']} → `{c['url']}` ({c['file']}:{c['line']})")

    # Matching
    lines.append("\n## Integration Map (FE → BE)\n")
    for m in matches:
        call = m["call"]
        if m["matches"]:
            for ep in m["matches"]:
                lines.append(f"- {call['lib']} {call['method']} `{normalize_url(call['url'])}` ↔ [{ep['method']}] `{ep.get('full_path') or ep.get('path')}` ({call['file']} → {ep['file']})")
        else:
            lines.append(f"- ⚠ No backend match for FE call: {call['method']} `{normalize_url(call['url'])}` ({call['file']}:{call['line']})")

    # Quick gaps guess
    lines.append("\n## Likely Gaps & Fix-First List (heuristic)\n")
    lines.append("- Ensure the frontend base API URL matches backend server origin and path prefix.")
    lines.append("- Fix CORS if FE and BE origins differ.")
    lines.append("- Create a Settings page if no route named like '/settings' or 'Settings' component exists.")
    lines.append("- Align FE payloads with BE Pydantic models.")
    lines.append("- Verify KuCoin credentials loading (env) and ccxt client instantiation flow.")
    
    if openapi_result and openapi_result['live_only_count'] > 0:
        lines.append("- **Review live-only endpoints** - these may be dynamically registered or missing from static analysis.")

    Path("REPORT.md").write_text("\n".join(lines), encoding="utf-8")

def main():
    py_files = walk_files(ROOT, PY_PATTERNS)
    fe_files = walk_files(ROOT, FE_PATTERNS)

    py_res = analyze_python(py_files)
    fe_res = analyze_frontend(fe_files)
    matches = match_calls_to_endpoints(fe_res["api_calls"], py_res["fastapi"]["routes"])

    # Create reports directory if it doesn't exist
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Try to fetch live OpenAPI spec
    live_openapi = fetch_live_openapi()
    openapi_result = None
    
    if live_openapi:
        print("✅ Live server detected - fetching OpenAPI spec...")
        live_endpoints = parse_openapi_endpoints(live_openapi)
        openapi_result = merge_endpoints(py_res["fastapi"]["routes"], live_endpoints)
        
        # Write live OpenAPI results
        live_report = {
            "live_openapi_spec": live_openapi,
            "endpoint_analysis": openapi_result,
            "timestamp": str(Path(__file__).stat().st_mtime),
            "server_info": {
                "title": live_openapi.get("info", {}).get("title", "Unknown"),
                "version": live_openapi.get("info", {}).get("version", "Unknown"),
                "description": live_openapi.get("info", {}).get("description", "")
            }
        }
        
        write_json("reports/openapi_live.json", live_report)
        
        print(f"📊 Live OpenAPI Analysis:")
        print(f"   - Static endpoints found: {openapi_result['static_count']}")
        print(f"   - Live endpoints found: {openapi_result['live_count']}")
        print(f"   - Merged total: {openapi_result['merged_count']}")
        print(f"   - Live-only endpoints: {openapi_result['live_only_count']}")
        
        if openapi_result['live_only_count'] > 0:
            print(f"   ⚠️  Found {openapi_result['live_only_count']} endpoints only in live API (not detected in static scan)")
            for ep in openapi_result['live_only_endpoints'][:5]:  # Show first 5
                print(f"      - [{ep['method']}] {ep['path']}")
            if len(openapi_result['live_only_endpoints']) > 5:
                print(f"      - ... and {len(openapi_result['live_only_endpoints']) - 5} more")
    else:
        print("⚠️  No live server detected at http://localhost:8000 - skipping OpenAPI analysis")

    write_json("graph.json", {"imports": py_res["imports"]})
    write_json("endpoints.json", py_res["fastapi"]["routes"])
    write_json("api_calls.json", fe_res["api_calls"])
    write_report(py_res, fe_res, matches, openapi_result)
    
    output_files = ["REPORT.md", "graph.json", "endpoints.json", "api_calls.json"]
    if openapi_result:
        output_files.append("reports/openapi_live.json")
    
    print(f"Done. Files written: {', '.join(output_files)}")

if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main()
