"""Conservative OpenAPI 3 compatibility checks. No remote reference fetching."""
import hashlib
import json

VERSION = "0.2.1"
METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def pointer_segment(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def finding(rule, file, message, evidence, severity="high", confidence="high", line=None,
            classification="breaking", action="Review consumers and preserve the previous contract or version the API."):
    identity = json.dumps([rule, file, line, evidence], sort_keys=True, default=str)
    return {"id": hashlib.sha256(identity.encode()).hexdigest()[:24], "severity": severity,
            "category": "api-compatibility", "file": file, "line": line,
            "message": message, "explanation": message, "evidence": evidence,
            "confidence": confidence, "recommended_action": action,
            "rule": rule, "rule_version": VERSION, "classification": classification,
            "kind": "confirmed-rule-violation" if confidence == "high" else "potential-risk"}


def _compare_openapi(base, head, filename="openapi.json"):
    out = []

    def emit(rule, message, path, before=None, after=None, classification="breaking"):
        out.append(finding(rule, filename, message,
            {"pointer": path, "before": before, "after": after},
            severity="info" if classification == "non-breaking" else "medium" if classification in ("unknown", "potentially-breaking") else "high",
            confidence="medium" if classification in ("unknown", "potentially-breaking") else "high",
            classification=classification))

    if not all(isinstance(d, dict) and str(d.get("openapi", "")).startswith("3.") and isinstance(d.get("paths"), dict) for d in (base, head)):
        emit("OAS.UNSUPPORTED", "Both inputs must be OpenAPI 3 documents with paths.", "/", classification="unknown")
        return out

    def resolve(value, doc, seen=()):
        if not isinstance(value, dict):
            return None
        ref = value.get("$ref")
        if ref is None:
            return value
        if not isinstance(ref, str) or not ref.startswith("#/") or ref in seen or len(seen) >= 20 or len(value) > 1:
            return None
        target = doc
        try:
            for key in ref[2:].split("/"):
                target = target[key.replace("~1", "/").replace("~0", "~")]
        except (KeyError, TypeError):
            return None
        return resolve(target, doc, seen + (ref,))

    def schema(a, b, path, direction, depth=0):
        # Inputs must not narrow; outputs must continue satisfying the old schema.
        a, b = resolve(a, base), resolve(b, head)
        if a is None or b is None or depth > 12:
            emit("OAS.SCHEMA_UNKNOWN", "Schema reference or recursion requires manual review.", path, classification="unknown")
            return
        if any(k in a or k in b for k in ("allOf", "anyOf", "oneOf", "not", "if", "then", "else", "unevaluatedProperties", "$dynamicRef")):
            emit("OAS.SCHEMA_COMPLEX", "Composed or conditional schema is not evaluated.", path, classification="unknown")
            return
        evaluated = {"type", "required", "enum", "nullable", "properties", "additionalProperties", "items", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "minItems", "maxItems", "pattern", "format", "const", "readOnly", "writeOnly"}
        annotations = {"title", "description", "default", "example", "examples", "deprecated", "externalDocs", "xml", "$id", "$schema", "$comment", "$defs", "definitions"}
        for key in sorted((a.keys() | b.keys()) - evaluated - annotations):
            if a.get(key) != b.get(key):
                emit("OAS.KEYWORD_UNKNOWN", f"Changed schema keyword is not evaluated: {key}", path + "/" + pointer_segment(key), classification="unknown")
        if a.get("type") != b.get("type"):
            emit("OAS.TYPE_CHANGED", "Schema type changed; compatibility requires review.", path, a.get("type"), b.get("type"), "potentially-breaking")
        ar, br = set(a.get("required", [])), set(b.get("required", []))
        changed = br - ar if direction == "request" else ar - br
        for prop in sorted(changed):
            emit("OAS.REQUIRED", f"{direction.title()} required-property contract changed: {prop}", path + "/required", sorted(ar), sorted(br))
        ae, be = a.get("enum"), b.get("enum")
        if ae != be:
            if direction == "request":
                breaking = be is not None and (ae is None or any(v not in be for v in ae))
            else:
                breaking = ae is not None and (be is None or any(v not in ae for v in be))
            if breaking:
                emit("OAS.ENUM", f"{direction.title()} enum compatibility changed.", path + "/enum", ae, be)
        if a.get("nullable", False) != b.get("nullable", False):
            if (direction == "request" and a.get("nullable")) or (direction == "response" and b.get("nullable")):
                emit("OAS.NULLABLE", f"{direction.title()} nullability changed incompatibly.", path, a.get("nullable", False), b.get("nullable", False))
        ap, bp = a.get("properties", {}), b.get("properties", {})
        if not isinstance(ap, dict) or not isinstance(bp, dict):
            emit("OAS.INVALID_PROPERTIES", "Invalid properties map.", path, classification="unknown")
            return
        for prop in sorted(ap.keys() & bp.keys()):
            schema(ap[prop], bp[prop], path + "/properties/" + pointer_segment(prop), direction, depth + 1)
        for prop in sorted(ap.keys() - bp.keys()):
            if direction == "response":
                emit("OAS.PROPERTY_REMOVED", f"Response property removed: {prop}", path + "/properties/" + pointer_segment(prop), "declared", "absent", "potentially-breaking")
            elif b.get("additionalProperties") is False:
                emit("OAS.PROPERTY_REJECTED", f"Previously accepted request property rejected: {prop}", path + "/properties/" + pointer_segment(prop))
        if a.get("additionalProperties", True) != b.get("additionalProperties", True):
            emit("OAS.ADDITIONAL_PROPERTIES", "Additional-properties policy changed.", path, a.get("additionalProperties", True), b.get("additionalProperties", True), "potentially-breaking")
        if "items" in a or "items" in b:
            schema(a.get("items", {}), b.get("items", {}), path + "/items", direction, depth + 1)
        for key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "minItems", "maxItems", "pattern", "format", "const", "readOnly", "writeOnly"):
            if a.get(key) != b.get(key):
                emit("OAS.CONSTRAINT", f"{direction.title()} constraint changed: {key}", path + "/" + pointer_segment(key), a.get(key), b.get(key), "potentially-breaking")

    def content(a, b, path, direction):
        for media in sorted(a.keys() - b.keys()):
            emit("OAS.MEDIA_REMOVED", f"{direction.title()} media type removed: {media}", path, media, None)
        if direction == "response":
            for media in sorted(b.keys() - a.keys()):
                emit("OAS.RESPONSE_MEDIA_ADDED", f"New response media type: {media}", path, None, media, "potentially-breaking")
        for media in sorted(a.keys() & b.keys()):
            schema(a[media].get("schema", {}), b[media].get("schema", {}), path + "/" + pointer_segment(media) + "/schema", direction)

    for path, old_path in sorted(base["paths"].items()):
        old_path = resolve(old_path, base)
        new_path = resolve(head["paths"].get(path, {}), head)
        if old_path is None or new_path is None:
            emit("OAS.PATH_UNKNOWN", "Unresolved path reference.", "/paths/" + pointer_segment(path), classification="unknown")
            continue
        for method in sorted(METHODS & old_path.keys()):
            pointer = f"/paths/{pointer_segment(path)}/{method}"
            if method not in new_path:
                emit("OAS.ENDPOINT_REMOVED", f"Removed endpoint: {method.upper()} {path}", pointer, "present", "absent")
                continue
            a, b = old_path[method], new_path[method]
            if not isinstance(a, dict) or not isinstance(b, dict):
                emit("OAS.OPERATION_UNKNOWN", "Invalid operation object.", pointer, classification="unknown")
                continue
            sec_a, sec_b = a.get("security", base.get("security", [])), b.get("security", head.get("security", []))
            if sec_a != sec_b:
                emit("OAS.SECURITY", "Authentication requirements changed.", pointer + "/security", sec_a, sec_b, "potentially-breaking")
            def params(doc, path_item, op):
                result, locations = {}, {}
                inputs = [(p, f"/paths/{pointer_segment(path)}/parameters/{i}") for i, p in enumerate(path_item.get("parameters", []))]
                inputs += [(p, pointer + f"/parameters/{i}") for i, p in enumerate(op.get("parameters", []))]
                for p, location in inputs:
                    p = resolve(p, doc)
                    if p is None:
                        emit("OAS.PARAM_UNKNOWN", "Unresolved parameter reference.", pointer, classification="unknown")
                    elif "name" in p and "in" in p:
                        result[(p["in"], p["name"])] = p
                        locations[(p["in"], p["name"])] = location
                return result, locations
            pa, locations_a = params(base, old_path, a)
            pb, locations_b = params(head, new_path, b)
            for key in sorted(pb.keys() - pa.keys()):
                if pb[key].get("required"):
                    emit("OAS.PARAM_REQUIRED", f"New required {key[0]} parameter: {key[1]}", pointer + "/parameters", None, key)
            for key in sorted(pa.keys() - pb.keys()):
                emit("OAS.PARAM_REMOVED", f"Removed {key[0]} parameter: {key[1]}", pointer + "/parameters", key, None, "potentially-breaking")
            for key in sorted(pa.keys() & pb.keys()):
                if not pa[key].get("required") and pb[key].get("required"):
                    emit("OAS.PARAM_REQUIRED", f"Parameter became required: {key[1]}", pointer + "/parameters", False, True)
                schema(pa[key].get("schema", {}), pb[key].get("schema", {}), locations_a[key] + "/schema", "request")
            ra, rb = resolve(a.get("requestBody", {}), base), resolve(b.get("requestBody", {}), head)
            if ra is None or rb is None:
                emit("OAS.BODY_UNKNOWN", "Unresolved request-body reference.", pointer, classification="unknown")
            else:
                if not ra.get("required") and rb.get("required"):
                    emit("OAS.BODY_REQUIRED", "Request body became required.", pointer + "/requestBody", False, True)
                content(ra.get("content", {}), rb.get("content", {}), pointer + "/requestBody/content", "request")
            responses_a, responses_b = a.get("responses", {}), b.get("responses", {})
            for code in sorted(responses_a.keys() - responses_b.keys()):
                emit("OAS.STATUS_REMOVED", f"Response status removed: {code}", pointer + "/responses", code, None, "potentially-breaking")
            for code in sorted(responses_b.keys() - responses_a.keys()):
                emit("OAS.STATUS_ADDED", f"New response status: {code}", pointer + "/responses", None, code, "potentially-breaking")
            for code in sorted(responses_a.keys() & responses_b.keys()):
                ra, rb = resolve(responses_a[code], base), resolve(responses_b[code], head)
                if ra is None or rb is None:
                    emit("OAS.RESPONSE_UNKNOWN", "Unresolved response reference.", pointer, classification="unknown")
                else:
                    content(ra.get("content", {}), rb.get("content", {}), pointer + "/responses/" + pointer_segment(code) + "/content", "response")
    for path, item in sorted(head["paths"].items()):
        item = resolve(item, head)
        old = resolve(base["paths"].get(path, {}), base)
        if item is not None and old is not None:
            for method in sorted((METHODS & item.keys()) - old.keys()):
                emit("OAS.ENDPOINT_ADDED", f"Added endpoint: {method.upper()} {path}", f"/paths/{pointer_segment(path)}/{method}", None, "present", "non-breaking")
    return out


def compare_openapi(base, head, filename="openapi.json"):
    """Malformed contracts yield an explicit unknown result, never a clean bill of health."""
    try:
        return _compare_openapi(base, head, filename)
    except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
        return [finding("OAS.INVALID_STRUCTURE", filename,
            "Contract contains an invalid or unsupported structure; comparison is inconclusive.",
            {"validation": "invalid-structure"}, severity="medium", confidence="medium",
            classification="unknown", action="Validate both documents with an OpenAPI validator and retry.")]
