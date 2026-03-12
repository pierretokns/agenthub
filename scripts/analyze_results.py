#!/usr/bin/env python3
"""
Analyze training results and generate insights.

Processes results.jsonl to:
- Calculate statistics (mean, std, best score, improvement rate)
- Identify best performing datasets
- Generate improvement recommendations
- Detect anomalies
- Export summary reports

Usage:
  python3 scripts/analyze_results.py
  python3 scripts/analyze_results.py --format json
  python3 scripts/analyze_results.py --format csv
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
from statistics import mean, stdev

RESULTS_FILE = Path("results.jsonl")


def load_results() -> List[Dict]:
    """Load all results from results.jsonl."""
    if not RESULTS_FILE.exists():
        print("❌ results.jsonl not found")
        return []

    results = []
    with open(RESULTS_FILE) as f:
        for i, line in enumerate(f, 1):
            try:
                result = json.loads(line)
                # Validate contamination
                if result.get("evaluation", {}).get("contamination", {}).get("passed"):
                    results.append(result)
                else:
                    print(f"⚠️  Result {i} contaminated (skipped)")
            except json.JSONDecodeError as e:
                print(f"⚠️  Result {i} malformed: {e}")

    return results


def calculate_statistics(results: List[Dict]) -> Dict:
    """Calculate statistics across all results."""
    if not results:
        return {}

    scores = [
        r.get("evaluation", {}).get("mteb_scores", {}).get("primary_score", 0)
        for r in results
    ]

    if len(scores) < 2:
        return {
            "count": len(scores),
            "best_score": max(scores) if scores else 0,
            "latest_score": scores[-1] if scores else 0,
            "improvement": 0,
        }

    return {
        "count": len(scores),
        "best_score": max(scores),
        "worst_score": min(scores),
        "latest_score": scores[-1],
        "mean_score": mean(scores),
        "std_dev": stdev(scores) if len(scores) > 1 else 0,
        "improvement": scores[-1] - scores[0],
        "improvement_rate": (scores[-1] - scores[0]) / len(scores),
        "runs_to_best": scores.index(max(scores)) + 1,
    }


def analyze_by_dataset(results: List[Dict]) -> Dict[str, List[Dict]]:
    """Group and analyze results by dataset."""
    by_dataset = {}

    for result in results:
        dataset_name = result.get("dataset", {}).get("name", "unknown")
        if dataset_name not in by_dataset:
            by_dataset[dataset_name] = []
        by_dataset[dataset_name].append(result)

    return by_dataset


def generate_recommendations(results: List[Dict], stats: Dict) -> List[str]:
    """Generate improvement recommendations."""
    recommendations = []

    if not results:
        return ["No results yet. Start with Phase 2 test run."]

    # Analyze trends
    scores = [
        r.get("evaluation", {}).get("mteb_scores", {}).get("primary_score", 0)
        for r in results
    ]

    if len(scores) >= 5:
        recent_gradient = (scores[-1] - scores[-5]) / 4 if len(scores) > 5 else 0
        if recent_gradient < 0.1:
            recommendations.append("⚠️  Score plateau detected. Consider switching datasets.")
        elif recent_gradient < 0.3:
            recommendations.append("📈 Slow improvement. May benefit from dataset change.")
        elif recent_gradient >= 0.5:
            recommendations.append("🚀 Rapid improvement! Continue current dataset.")

    best_dataset = None
    best_score = 0
    by_dataset = analyze_by_dataset(results)
    for dataset, runs in by_dataset.items():
        dataset_scores = [
            r.get("evaluation", {}).get("mteb_scores", {}).get("primary_score", 0)
            for r in runs
        ]
        avg = mean(dataset_scores) if dataset_scores else 0
        if avg > best_score:
            best_score = avg
            best_dataset = dataset

    if best_dataset:
        recommendations.append(f"✨ Best dataset: {best_dataset} (avg: {best_score:.2f})")

    if stats.get("count", 0) < 5:
        recommendations.append(f"📊 Need {5 - stats.get('count', 0)} more runs for statistically significant results")

    return recommendations


def print_summary(results: List[Dict]):
    """Print formatted summary to stdout."""
    stats = calculate_statistics(results)
    by_dataset = analyze_by_dataset(results)
    recommendations = generate_recommendations(results, stats)

    print("\n" + "=" * 70)
    print("RESULTS ANALYSIS SUMMARY")
    print("=" * 70 + "\n")

    if not results:
        print("No valid results yet.")
        return

    print(f"📊 Overall Statistics")
    print(f"  Total runs: {stats.get('count', 0)}")
    print(f"  Best score: {stats.get('best_score', 0):.2f}")
    print(f"  Latest score: {stats.get('latest_score', 0):.2f}")
    print(f"  Improvement: {stats.get('improvement', 0):+.2f} points")
    print(f"  Improvement rate: {stats.get('improvement_rate', 0):.4f} points/run")
    if stats.get("std_dev"):
        print(f"  Std deviation: {stats['std_dev']:.2f}")
    print()

    print(f"📈 Results by Dataset")
    for dataset, runs in sorted(by_dataset.items()):
        scores = [
            r.get("evaluation", {}).get("mteb_scores", {}).get("primary_score", 0)
            for r in runs
        ]
        avg = mean(scores) if scores else 0
        print(f"  {dataset}: {len(runs)} runs, avg score: {avg:.2f}")
        if scores:
            print(f"    Range: {min(scores):.2f} - {max(scores):.2f}")
    print()

    print("💡 Recommendations")
    for rec in recommendations:
        print(f"  {rec}")
    print()

    print("=" * 70 + "\n")


def export_csv(results: List[Dict], output_file: str = "analysis.csv"):
    """Export results to CSV."""
    import csv

    if not results:
        print("No results to export")
        return

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Iteration",
            "Dataset",
            "Primary Score",
            "STS Mean",
            "Retrieval Mean",
            "Contamination Rate",
            "Contamination Passed",
        ])

        for i, result in enumerate(results, 1):
            eval_data = result.get("evaluation", {})
            mteb = eval_data.get("mteb_scores", {})
            contam = eval_data.get("contamination", {})

            writer.writerow([
                i,
                result.get("dataset", {}).get("name", "?"),
                mteb.get("primary_score", 0),
                mteb.get("sts_mean", 0),
                mteb.get("retrieval_mean", 0),
                f"{contam.get('overall_rate', 0):.4f}",
                contam.get("passed", False),
            ])

    print(f"✅ Exported to {output_file}")


def export_json(results: List[Dict], output_file: str = "analysis.json"):
    """Export analysis to JSON."""
    stats = calculate_statistics(results)
    by_dataset = analyze_by_dataset(results)
    recommendations = generate_recommendations(results, stats)

    analysis = {
        "timestamp": datetime.now().isoformat(),
        "statistics": stats,
        "by_dataset": {
            dataset: {
                "count": len(runs),
                "scores": [
                    r.get("evaluation", {}).get("mteb_scores", {}).get("primary_score", 0)
                    for r in runs
                ],
            }
            for dataset, runs in by_dataset.items()
        },
        "recommendations": recommendations,
    }

    with open(output_file, "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"✅ Exported to {output_file}")


def main():
    """Main analysis flow."""
    import sys

    # Parse args
    format_type = "text"
    if "--format" in sys.argv:
        idx = sys.argv.index("--format")
        if idx + 1 < len(sys.argv):
            format_type = sys.argv[idx + 1]

    # Load and analyze
    results = load_results()

    if format_type == "csv":
        export_csv(results)
    elif format_type == "json":
        export_json(results)
    else:
        print_summary(results)


if __name__ == "__main__":
    main()
