"""Bounded, deterministic static inspection; customer code is never imported or run."""
import ast
import io
import json
import re
import stat
import zipfile
from pathlib import PurePosixPath
from .contracts import VERSION, compare_openapi, finding

MAX_BYTES = 8_000_000
MAX_FILES = 400
MAX_FILE_BYTES = 300_000
SUPPORTED = {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml", ".txt", ".toml", ".env"}


class Sources(dict):
    def __init__(self):
        super().__init__()
        self.skipped = []


def read_zip(data):
    if len(data) > MAX_BYTES:
        raise ValueError("ZIP exceeds upload limit")
    files = Sources()
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 5000:
                raise ValueError("ZIP contains too many entries")
            total = 0
            seen = set()
            for info in entries:
                name = info.filename
                p = PurePosixPath(name)
                if p.is_absolute() or ".." in p.parts or "\\" in name or re.match(r"^[A-Za-z]:", name) or "\x00" in name:
                    raise ValueError("Unsafe ZIP path")
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError("ZIP symlinks are not supported")
                if info.flag_bits & 1:
                    raise ValueError("Encrypted ZIP entries are not supported")
                if str(p) in seen:
                    raise ValueError("Duplicate ZIP path")
                seen.add(str(p))
                if info.is_dir():
                    continue
                if p.suffix.lower() not in SUPPORTED and p.name not in ("Dockerfile", ".env"):
                    files.skipped.append({"file": name, "reason": "unsupported-extension"})
                    continue
                if any(part in (".git", "node_modules", ".venv", "dist", "vendor") for part in p.parts):
                    files.skipped.append({"file": name, "reason": "excluded-directory"})
                    continue
                if info.file_size > MAX_FILE_BYTES:
                    files.skipped.append({"file": name, "reason": "file-size-limit"})
                    continue
                if len(files) >= MAX_FILES:
                    files.skipped.append({"file": name, "reason": "file-count-limit"})
                    continue
                total += info.file_size
                if total > MAX_BYTES:
                    raise ValueError("Extracted source exceeds size limit")
                with archive.open(info) as stream:
                    raw = stream.read(MAX_FILE_BYTES + 1)
                if len(raw) > MAX_FILE_BYTES:
                    raise ValueError("ZIP entry exceeds declared limit")
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    files.skipped.append({"file": name, "reason": "non-utf8"})
                    continue
                if "\x00" in text:
                    files.skipped.append({"file": name, "reason": "binary-content"})
                    continue
                files[str(p)] = text
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, OSError) as exc:
        raise ValueError("Invalid or unsupported ZIP") from exc
    if not files:
        raise ValueError("No supported UTF-8 sources found")
    # GitHub archives wrap every path in a revision-specific directory.
    all_paths = list(files) + [entry["file"] for entry in files.skipped]
    roots = {PurePosixPath(path).parts[0] for path in all_paths}
    if len(roots) == 1 and all(len(PurePosixPath(path).parts) > 1 for path in all_paths):
        normalized = {str(PurePosixPath(*PurePosixPath(path).parts[1:])): source for path, source in files.items()}
        files.clear()
        files.update(normalized)
        for entry in files.skipped:
            entry["file"] = str(PurePosixPath(*PurePosixPath(entry["file"]).parts[1:]))
    return files


def _name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _name(node.value) + "." + node.attr
    return ""


def _signature(node):
    args = node.args
    ordered = args.posonlyargs + args.args
    return {"positional": [a.arg for a in ordered], "positional_only": len(args.posonlyargs),
            "required_positional": len(ordered) - len(args.defaults),
            "keyword_only": [a.arg for a in args.kwonlyargs],
            "required_keyword_only": [a.arg for a, d in zip(args.kwonlyargs, args.kw_defaults) if d is None],
            "varargs": args.vararg is not None, "kwargs": args.kwarg is not None,
            "async": isinstance(node, ast.AsyncFunctionDef)}


def _python(source, file, found):
    routes, functions, imports = {}, {}, []
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError) as exc:
        f = finding("PY.SYNTAX", file, f"Python syntax error at line {getattr(exc, 'lineno', None)}",
                    {"parser_error": type(exc).__name__}, line=getattr(exc, "lineno", None),
                    action="Fix the Python parser error before deploying.")
        f["category"] = "syntax"
        found.append(f)
        return routes, functions, imports, False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            functions[node.name] = (node.lineno, _signature(node))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((a.name, node.lineno) for a in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(("." * node.level + node.module, node.lineno))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                method = decorator.func.attr
                # Named app/router objects only: mounted prefixes and aliases are not resolved.
                if method in {"get", "post", "put", "patch", "delete", "head", "options"} and _name(decorator.func.value) in {"app", "router"}:
                    path = decorator.args[0] if decorator.args else next((k.value for k in decorator.keywords if k.arg == "path"), None)
                    if isinstance(path, ast.Constant) and isinstance(path.value, str):
                        routes[f"{method.upper()} {path.value}"] = {"file": file, "line": decorator.lineno, "handler": node.name}
        if isinstance(node, ast.Call):
            name = _name(node.func)
            rule = None
            if name in ("eval", "exec", "pickle.loads", "pickle.load"):
                rule = "PY.DANGEROUS_CALL"
            if name.startswith("subprocess.") and any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords):
                rule = "PY.SHELL"
            if rule:
                f = finding(rule, file, f"Review potentially dangerous call: {name}", {"call": name},
                    severity="medium", confidence="medium", line=node.lineno, classification="potentially-breaking",
                    action="Verify input trust and use a non-executing parser or argument-array subprocess API.")
                f["category"] = "security-review"
                found.append(f)
    return routes, functions, imports, True


def analyze(files, baseline=None):
    found, routes, functions, imports, parsed = [], {}, {}, [], {}
    skipped = getattr(files, "skipped", [])
    skipped_paths = {entry["file"] for entry in skipped}
    baseline_skipped = getattr(baseline, "skipped", [])
    for filename, source in sorted(files.items()):
        if filename.endswith(".py"):
            r, f, i, ok = _python(source, filename, found)
            routes.update(r)
            functions[filename] = f
            imports.extend({"source": filename, "target": module, "line": line, "kind": "python-import", "certainty": "declared-import-unresolved-target"} for module, line in i)
            parsed[filename] = ok
        if source.startswith("version https://git-lfs.github.com/spec/"):
            f = finding("SOURCE.LFS", filename, "Git LFS pointer was not resolved.", {"format": "git-lfs"}, severity="info", confidence="medium", classification="unknown", action="Provide the actual source object for analysis.")
            f["category"] = "coverage"
            found.append(f)
    unknown_python = {path for path in skipped_paths if path.endswith(".py")} | {path for path, ok in parsed.items() if not ok}
    comparison_unknown = sorted((skipped_paths & set(baseline or {})) | unknown_python)
    if baseline is not None:
        if comparison_unknown:
            f = finding("SOURCE.COMPARISON_INCOMPLETE", "coverage",
                "Some proposed sources could not be inspected. Removal checks involving omitted files or unresolved Python routes are inconclusive.",
                {"uninspected_files": comparison_unknown}, severity="info", confidence="medium", classification="unknown",
                action="Provide supported, readable source within the size limits and rerun the comparison.")
            f["category"] = "coverage"
            found.append(f)
        old_routes = {}
        for filename, source in sorted(baseline.items()):
            if filename.endswith(".py"):
                old_r, old_f, _, old_ok = _python(source, filename, [])
                old_routes.update(old_r)
                if filename in skipped_paths or not old_ok or (filename in parsed and not parsed[filename]):
                    continue
                for name, (line, signature) in old_f.items():
                    current = functions.get(filename, {}).get(name)
                    if current is None:
                        f = finding("PY.FUNCTION_REMOVED", filename, f"Public module function removed: {name}", {"function": name, "baseline_signature": signature}, line=line,
                                    confidence="medium", classification="potentially-breaking")
                        f["category"] = "breaking-change"
                        found.append(f)
                    elif current[1] != signature:
                        f = finding("PY.SIGNATURE_CHANGED", filename, f"Public function signature changed: {name}", {"function": name, "before": signature, "after": current[1]},
                                    line=current[0], severity="medium", confidence="medium", classification="potentially-breaking")
                        f["category"] = "breaking-change"
                        found.append(f)
        for route in sorted(old_routes.keys() - routes.keys()):
            old = old_routes[route]
            # A route may have moved to any omitted Python file. Do not infer absence.
            if unknown_python or old["file"] in skipped_paths:
                continue
            f = finding("PY.ROUTE_REMOVED", old["file"], f"Removed endpoint: {route}", {"route": route, "baseline_location": old}, line=old["line"], confidence="medium", classification="potentially-breaking")
            f["category"] = "breaking-change"
            found.append(f)
        for filename in sorted(baseline.keys() & files.keys()):
            if filename.endswith(".json"):
                a = None
                try:
                    a = json.loads(baseline[filename])
                    b = json.loads(files[filename])
                    if isinstance(a, dict) and isinstance(b, dict) and ("openapi" in a or "openapi" in b):
                        found.extend(compare_openapi(a, b, filename))
                except (ValueError, TypeError, AttributeError, RecursionError):
                    if "openapi" in filename.lower() or (isinstance(a, dict) and "openapi" in a):
                        found.append(finding("OAS.INVALID", filename, "OpenAPI JSON could not be compared.", {"format": "invalid-json-or-structure"}, severity="medium", confidence="medium", classification="unknown"))
            if filename.rsplit("/", 1)[-1] in {"requirements.txt", "package.json", "package-lock.json", "pyproject.toml", "poetry.lock", "Dockerfile"} and baseline[filename] != files[filename]:
                f = finding("CONFIG.CHANGED", filename, "Dependency or build configuration changed; review compatibility.", {"changed": True}, severity="medium", confidence="medium", classification="potentially-breaking",
                            action="Review dependency release notes and run tests in an isolated environment. Vulnerability lookup was not performed.")
                f["category"] = "dependency-review"
                found.append(f)
        for filename in sorted(baseline.keys() - files.keys()):
            if filename in skipped_paths:
                continue
            if filename.endswith(".json"):
                try:
                    old = json.loads(baseline[filename])
                    if isinstance(old, dict) and "openapi" in old:
                        found.append(finding("OAS.DOCUMENT_REMOVED", filename,
                            "Baseline API contract file is absent in the proposed source; endpoint availability is unknown.",
                            {"baseline_contract": filename}, confidence="medium", classification="unknown"))
                except (ValueError, RecursionError):
                    pass
    found.sort(key=lambda f: (f["file"], f.get("line") or 0, f["rule"], f["id"]))
    weights = {"critical": 40, "high": 20, "medium": 7, "low": 2, "info": 0}
    score = min(100, sum(weights[f["severity"]] for f in found))
    risk = "high" if any(f["severity"] in {"high", "critical"} for f in found) else "medium" if any(f["severity"] == "medium" for f in found) else "low"
    unsupported = sorted(f for f in files if not f.endswith(".py") and not (f.endswith(".json") and "openapi" in files[f]))
    return {"engine_version": VERSION, "risk_level": risk, "risk_score": score,
            "score_explanation": "Capped sum of rule weights: critical 40, high 20, medium 7, low 2, info 0. This is a prioritization index, not a failure probability.",
            "files_scanned": len(files), "python_files_parsed": sum(parsed.values()),
            "routes_detected": sorted(routes), "route_evidence": routes, "findings": found,
            "dependency_graph": {"edges": imports, "limitations": "Import declarations only; targets and runtime relationships are not resolved."},
            "coverage": {"skipped": skipped, "baseline_skipped": baseline_skipped,
                         "comparison_unknown_files": comparison_unknown,
                         "route_removal_checks_complete": not bool(unknown_python),
                         "files_without_language_analysis": unsupported, "baseline_provided": baseline is not None},
            "simulation": {"status": "not-executed", "reason": "No isolated execution worker is configured. Static comparisons are not executed tests."},
            "limitations": "Static Python AST and selected OpenAPI JSON rules only. Python routes use literal app/router decorators; mounted prefixes, aliases, dynamic routes, classes, and response models are not resolved. JavaScript/TypeScript are retained but not parsed. No code execution, vulnerability database lookup, or guarantee of safety. Skipped files and unresolved contracts require review."}
