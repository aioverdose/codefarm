"""Convert code quality signals into CodeFarm nutrients."""
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from codefarm_common import ROOT, read_json

RULES_PATH = ROOT / "digestive-engine" / "quality-rules.json"

def score_test_pass_rate(rate: float) -> int:
    if rate >= 1.0: return 100
    if rate >= 0.9: return 80
    if rate >= 0.7: return 50
    if rate > 0: return 10
    return -20

def score_complexity(max_complexity: int) -> int:
    if max_complexity <= 5: return 100
    if max_complexity <= 10: return 70
    if max_complexity <= 20: return 40
    return 10

def score_documentation(coverage: float) -> int:
    if coverage >= 1.0: return 100
    if coverage >= 0.8: return 80
    if coverage >= 0.5: return 50
    return 20

def score_security(findings: list[dict[str, Any]]) -> int:
    severities = [str(item.get("severity", "low")).lower() for item in findings]
    if any(level in {"high", "critical"} for level in severities): return 0
    medium = severities.count("medium")
    low = severities.count("low")
    if medium or low > 2: return 50
    if low: return 80
    return 100

def score_style(issue_count: int) -> int:
    if issue_count == 0: return 100
    if issue_count <= 5: return 80
    if issue_count <= 15: return 50
    return 20

def calculate_nutrients(analysis: dict[str, Any], task_multiplier: float = 1.0) -> dict[str, Any]:
    rules = read_json(RULES_PATH, {})
    weights = {k: v.get("weight", 0) for k, v in rules.get("quality_rules", {}).items()}
    multiplier = float(rules.get("base_calorie_multiplier", 10)) * float(task_multiplier)
    component_scores = {
        "test_pass_rate": score_test_pass_rate(float(analysis.get("test_pass_rate", 0))),
        "code_complexity": score_complexity(int(analysis.get("max_complexity", 99))),
        "documentation_coverage": score_documentation(float(analysis.get("documentation_coverage", 0))),
        "security_score": score_security(list(analysis.get("security_findings", []))),
        "style_compliance": score_style(int(analysis.get("style_issues", 99))),
    }
    weighted_quality = sum(component_scores[name] * float(weights.get(name, 0)) for name in component_scores)
    return {"component_scores": component_scores, "weighted_quality": round(weighted_quality, 2), "nutrient_value": max(0, round(weighted_quality * multiplier))}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis_json")
    parser.add_argument("--task-multiplier", type=float, default=1.0)
    args = parser.parse_args()
    print(calculate_nutrients(read_json(Path(args.analysis_json), {}), args.task_multiplier))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
