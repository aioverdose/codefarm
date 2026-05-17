"""Static analyzer and digestion entry point for CodeFarm organism output."""
from __future__ import annotations
import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from codefarm_common import ROOT, log_event, read_json, utc_now, write_json
from nutrient_calculator import calculate_nutrients

DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__"}
DANGEROUS_MODULES = {"subprocess", "socket", "shutil"}

def cyclomatic_proxy(tree: ast.AST) -> int:
    branch_nodes = (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler, ast.BoolOp, ast.IfExp, ast.Match)
    return 1 + sum(1 for node in ast.walk(tree) if isinstance(node, branch_nodes))

def documentation_coverage(tree: ast.AST) -> float:
    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    if not functions:
        return 1.0 if ast.get_docstring(tree) else 0.0
    return sum(1 for node in functions if ast.get_docstring(node)) / len(functions)

def security_findings(tree: ast.AST) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_CALLS:
            findings.append({"severity": "high", "message": f"dangerous call: {node.func.id}"})
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in DANGEROUS_MODULES:
                    findings.append({"severity": "medium", "message": f"sensitive import: {alias.name}"})
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in DANGEROUS_MODULES:
            findings.append({"severity": "medium", "message": f"sensitive import: {node.module}"})
    return findings

def style_issues(source: str) -> int:
    issues = 0
    for line in source.splitlines():
        if len(line) > 100: issues += 1
        if line.rstrip() != line: issues += 1
        if "TODO" in line or "pass  #" in line: issues += 1
    return issues

def run_tests(output_file: Path, task: dict[str, Any]) -> float:
    if task.get("expected_function") != "safe_json_loads":
        return 0.0
    test_code = f'''
import importlib.util
from pathlib import Path
module_path = Path(r"{output_file}")
spec = importlib.util.spec_from_file_location("organism_output", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.safe_json_loads('{{"a": 1}}') == {{"a": 1}}
assert module.safe_json_loads('not json', default={{"fallback": True}}) == {{"fallback": True}}
assert module.safe_json_loads('null', default=3) is None
'''
    result = subprocess.run([sys.executable, "-c", test_code], cwd=str(ROOT), text=True, capture_output=True, timeout=10)
    return 1.0 if result.returncode == 0 else 0.0

def analyze_file(output_file: Path, task: dict[str, Any] | None = None) -> dict[str, Any]:
    task = task or {}
    source = output_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {"syntax_ok": False, "error": str(exc), "test_pass_rate": 0.0, "max_complexity": 99, "documentation_coverage": 0.0, "security_findings": [{"severity": "high", "message": "syntax error"}], "style_issues": 20}
    return {"syntax_ok": True, "test_pass_rate": run_tests(output_file, task), "max_complexity": cyclomatic_proxy(tree), "documentation_coverage": documentation_coverage(tree), "security_findings": security_findings(tree), "style_issues": style_issues(source)}

def digest(output_file: Path, task_path: Path | None = None) -> dict[str, Any]:
    task = read_json(task_path, {}) if task_path else {}
    analysis = analyze_file(output_file, task)
    nutrients = calculate_nutrients(analysis, float(task.get("nutrient_multiplier", 1.0)))
    payload = {"digested_at": utc_now(), "source": str(output_file), "task": task.get("id"), "analysis": analysis, "nutrients": nutrients}
    nutrient_id = f"nutrient-{Path(output_file).stem}-{utc_now().replace(':', '').replace('+', 'Z')}.json"
    write_json(ROOT / "nutrient-pool" / "available" / nutrient_id, payload)
    log_event(f"DIGESTED source={output_file} calories={nutrients['nutrient_value']}")
    return payload

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_file")
    parser.add_argument("--task")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = digest(Path(args.output_file), Path(args.task) if args.task else None)
    print(json.dumps(payload, indent=2) if args.json else payload["nutrients"]["nutrient_value"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
