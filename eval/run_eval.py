"""
VoiceActions AI — Eval Harness Runner
The unfair advantage: 20 test cases, automated scoring, run after every change.
"""

import json
import sys
import time
import os
import argparse
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def load_test_cases(category=None):
    """Load test cases, optionally filtered by category."""
    with open(os.path.join(os.path.dirname(__file__), "test_cases.json")) as f:
        data = json.load(f)

    cases = data["test_cases"]
    if category:
        cases = [c for c in cases if c["category"] == category]
    return cases


def evaluate_result(test_case, result):
    """Score a single result against expected values."""
    scores = {}
    analysis = result.get("analysis", {})

    actual_actions = len(analysis.get("actions", []))
    actual_conflicts = len(analysis.get("conflicts", []))
    actual_ambiguities = len(analysis.get("ambiguities", []))

    expected_actions = test_case["expected_actions"]
    expected_conflicts = test_case["expected_conflicts"]
    expected_ambiguities = test_case["expected_ambiguities"]

    # Action extraction accuracy
    if expected_actions == 0:
        scores["action_accuracy"] = 1.0 if actual_actions == 0 else 0.5
    else:
        scores["action_accuracy"] = min(actual_actions / expected_actions, 1.0)

    # Conflict detection
    if expected_conflicts == 0:
        scores["conflict_precision"] = 1.0 if actual_conflicts == 0 else 0.0
        scores["conflict_recall"] = 1.0
    else:
        scores["conflict_recall"] = min(actual_conflicts / expected_conflicts, 1.0)
        scores["conflict_precision"] = (
            1.0
            if actual_conflicts <= expected_conflicts + 1
            else max(0, 1.0 - (actual_conflicts - expected_conflicts) * 0.2)
        )

    # Ambiguity detection
    if expected_ambiguities == 0:
        scores["ambiguity_accuracy"] = 1.0 if actual_ambiguities <= 1 else 0.5
    else:
        scores["ambiguity_accuracy"] = min(
            actual_ambiguities / expected_ambiguities, 1.0
        )

    # Overall
    scores["overall"] = (
        scores["action_accuracy"] * 0.4
        + scores["conflict_recall"] * 0.3
        + scores["conflict_precision"] * 0.15
        + scores["ambiguity_accuracy"] * 0.15
    )

    return scores


def run_eval(category=None, verbose=True):
    """Run evaluation suite."""
    cases = load_test_cases(category)
    print(f"\n{'='*60}")
    print(f"  VoiceActions AI — Eval Harness")
    print(f"  {len(cases)} test cases | Category: {category or 'all'}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    results = []

    for i, case in enumerate(cases):
        if not case["input_text"]:
            if verbose:
                print(f"  [{i+1}/{len(cases)}] {case['id']} — SKIP (empty input)")
            continue

        if verbose:
            print(f"  [{i+1}/{len(cases)}] {case['id']} ({case['category']})...", end=" ")

        start = time.time()

        try:
            # Call the backend API
            import httpx

            response = httpx.post(
                "http://localhost:8000/api/process-text",
                json={"text": case["input_text"]},
                timeout=60,
            )
            result = response.json()
            latency = int((time.time() - start) * 1000)

            scores = evaluate_result(case, result)
            result_entry = {
                "id": case["id"],
                "category": case["category"],
                "scores": scores,
                "latency_ms": latency,
                "actual_actions": len(result.get("analysis", {}).get("actions", [])),
                "actual_conflicts": len(result.get("analysis", {}).get("conflicts", [])),
                "actual_ambiguities": len(result.get("analysis", {}).get("ambiguities", [])),
                "expected_actions": case["expected_actions"],
                "expected_conflicts": case["expected_conflicts"],
                "expected_ambiguities": case["expected_ambiguities"],
                "confidence": result.get("final_confidence", 0),
                "cost_usd": result.get("total_cost_usd", 0),
            }
            results.append(result_entry)

            if verbose:
                status = "✓" if scores["overall"] >= 0.7 else "△" if scores["overall"] >= 0.4 else "✗"
                print(
                    f"{status} overall={scores['overall']:.2f} "
                    f"actions={result_entry['actual_actions']}/{case['expected_actions']} "
                    f"conflicts={result_entry['actual_conflicts']}/{case['expected_conflicts']} "
                    f"latency={latency}ms"
                )

        except Exception as e:
            if verbose:
                print(f"✗ ERROR: {str(e)[:80]}")
            results.append(
                {"id": case["id"], "category": case["category"], "error": str(e)}
            )

    # Summary
    valid = [r for r in results if "scores" in r]
    if valid:
        avg_overall = sum(r["scores"]["overall"] for r in valid) / len(valid)
        avg_action = sum(r["scores"]["action_accuracy"] for r in valid) / len(valid)
        avg_conflict_recall = sum(r["scores"]["conflict_recall"] for r in valid) / len(valid)
        avg_conflict_precision = sum(r["scores"]["conflict_precision"] for r in valid) / len(valid)
        avg_latency = sum(r["latency_ms"] for r in valid) / len(valid)
        total_cost = sum(r["cost_usd"] for r in valid)

        print(f"\n{'='*60}")
        print(f"  RESULTS SUMMARY")
        print(f"{'='*60}")
        print(f"  Tests run:              {len(valid)}/{len(cases)}")
        print(f"  Overall score:          {avg_overall:.2%}")
        print(f"  Action accuracy:        {avg_action:.2%}")
        print(f"  Conflict recall:        {avg_conflict_recall:.2%}")
        print(f"  Conflict precision:     {avg_conflict_precision:.2%}")
        print(f"  Avg latency:            {avg_latency:.0f}ms")
        print(f"  Total cost:             ${total_cost:.4f}")
        print(f"  Cost per query:         ${total_cost/len(valid):.5f}")
        print(f"{'='*60}\n")

    # Save results
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"eval_{timestamp}.json")

    with open(results_file, "w") as f:
        json.dump({"timestamp": timestamp, "category": category, "results": results}, f, indent=2)

    print(f"  Results saved to: {results_file}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VoiceActions AI Eval Harness")
    parser.add_argument("--all", action="store_true", help="Run all test cases")
    parser.add_argument("--category", type=str, help="Filter by category: clean, conflict, hindi-english, ambiguous, edge, stress")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    category = args.category if args.category else None
    verbose = not args.quiet

    run_eval(category=category, verbose=verbose)
