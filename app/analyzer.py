"""Read-only source inspection. Never executes repository code."""
import ast
import io
import re
import zipfile
from pathlib import PurePosixPath

MAX_BYTES = 8_000_000
ROUTES = re.compile(r'@?(?:app|router)\.(get|post|put|patch|delete)\(\s*["\']([^"\']+)', re.I)
SUSPICIOUS = ("eval(", "exec(", "shell=True", "pickle.loads(")

def analyze(files, baseline=None):
    found, routes = [], set()
    for filename, source in files.items():
        if filename.endswith(".py"):
            try:
                ast.parse(source)
            except SyntaxError as exc:
                found.append({"severity":"high","file":filename,"message":f"Python syntax error at line {exc.lineno}","category":"syntax"})
        routes.update(f"{method.upper()} {path}" for method,path in ROUTES.findall(source))
        for pattern in SUSPICIOUS:
            if pattern in source:
                found.append({"severity":"medium","file":filename,"message":f"Review potentially dangerous pattern: {pattern}","category":"review"})
    if baseline is not None:
        old = {f"{method.upper()} {path}" for source in baseline.values() for method,path in ROUTES.findall(source)}
        for route in sorted(old-routes):
            found.append({"severity":"high","file":"API","message":f"Removed endpoint: {route}","category":"breaking-change"})
    risk = "high" if any(f["severity"]=="high" for f in found) else "medium" if found else "low"
    return {"risk_level":risk,"files_scanned":len(files),"routes_detected":sorted(routes),"findings":found,
            "limitations":"Heuristic static checks only. Not a proof of security or production readiness."}

def read_zip(data):
    if len(data)>MAX_BYTES: raise ValueError("ZIP exceeds upload limit")
    try: z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e: raise ValueError("Invalid ZIP") from e
    files, total = {}, 0
    with z:
        for info in z.infolist():
            p = PurePosixPath(info.filename)
            if info.is_dir() or p.is_absolute() or ".." in p.parts: continue
            if p.suffix.lower() not in (".py",".js",".ts",".tsx",".jsx",".json",".yaml",".yml"): continue
            if any(part in (".git","node_modules",".venv","dist") for part in p.parts): continue
            if info.file_size>300_000 or len(files)>=400: continue
            total += info.file_size
            if total>MAX_BYTES: raise ValueError("Extracted source exceeds size limit")
            try: files[str(p)] = z.read(info).decode("utf-8")
            except UnicodeDecodeError: pass
    if not files: raise ValueError("No supported UTF-8 sources found")
    return files
