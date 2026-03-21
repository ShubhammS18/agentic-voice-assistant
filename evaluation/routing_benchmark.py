# evaluation/routing_benchmark.py
"""
Routing accuracy benchmark — 30 labelled queries (10 per domain).
Tests the semantic router directly via rewrite_query + route_query.
Run: python -m evaluation.routing_benchmark
Produces: evaluation/results/routing_report.md
"""
import asyncio
import time
import os
from datetime import datetime

# 30 labelled queries — 10 per domain
BENCHMARK_QUERIES = [
    # RAG — document/policy/knowledge base queries
    ("What are the Golden Visa eligibility requirements?",           "rag"),
    ("Explain the DIFC employment contract rules",                   "rag"),
    ("What does the company policy say about remote work?",          "rag"),
    ("Tell me about the product documentation for onboarding",       "rag"),
    ("What are the technical guidelines for API integration?",       "rag"),
    ("Summarise the internal compliance procedures",                 "rag"),
    ("What does the knowledge base say about data retention?",       "rag"),
    ("Explain the historical background from the archived documents","rag"),
    ("What are the rules according to our internal policy manual?",  "rag"),
    ("Find information about procedures in the document archive",    "rag"),

    # WEB — current events/real-time queries
    ("What happened in AI news today?",                             "web"),
    ("What is the current price of NVIDIA stock?",                  "web"),
    ("What are the latest developments in large language models?",  "web"),
    ("Who won the election results announced today?",               "web"),
    ("What is the weather forecast for this week?",                 "web"),
    ("What are the breaking news headlines right now?",             "web"),
    ("What did OpenAI announce recently?",                          "web"),
    ("What is the latest iPhone model released?",                   "web"),
    ("What happened at the AI conference this week?",               "web"),
    ("What are the current interest rates announced today?",        "web"),

    # DATA — structured facts/system specs queries
    ("What is the tech stack of this system?",                    "data"),
    ("What is the latency budget breakdown?",                     "data"),
    ("What languages does this system support?",                  "data"),
    ("What routing method does this project use?",                "data"),
    ("Which web search provider is used in this project?",        "data"),
    ("What are the configuration values for this system?",        "data"),
    ("What version of the model is being used?",                  "data"),
    ("What are the system specifications and settings?",          "data"),
    ("What is the supported language for this voice assistant?",  "data"),
    ("What infrastructure components are in this project?",       "data")]


async def run_benchmark():
    from app.rewriter import rewrite_query
    from app.router import route_query

    print(f"Running routing benchmark — {len(BENCHMARK_QUERIES)} queries")
    print("=" * 60)

    results = []
    correct = 0
    domain_stats = {"rag": {"correct": 0, "total": 0},
                    "web": {"correct": 0, "total": 0},
                    "data": {"correct": 0, "total": 0}}

    for i, (query, expected) in enumerate(BENCHMARK_QUERIES):
        t_start = time.perf_counter()
        sub_queries, rewrite_ms = await rewrite_query(query)
        route, route_ms = route_query(sub_queries)
        total_ms = int((time.perf_counter() - t_start) * 1000)

        is_correct = route == expected
        if is_correct:
            correct += 1
        domain_stats[expected]["total"] += 1
        if is_correct:
            domain_stats[expected]["correct"] += 1

        status = "✓" if is_correct else "✗"
        print(f"{status} [{i+1:2d}] expected={expected:4s} got={route:4s} "
                f"({total_ms}ms) — {query[:55]}")

        results.append({
            "query": query,
            "expected": expected,
            "predicted": route,
            "correct": is_correct,
            "rewrite_ms": rewrite_ms,
            "route_ms": route_ms,
            "total_ms": total_ms,
            "sub_queries": sub_queries})

    overall_accuracy = correct / len(BENCHMARK_QUERIES) * 100
    print("=" * 60)
    print(f"Overall accuracy: {correct}/{len(BENCHMARK_QUERIES)} = {overall_accuracy:.1f}%")
    for domain, stats in domain_stats.items():
        acc = stats["correct"] / stats["total"] * 100
        print(f"  {domain:4s}: {stats['correct']}/{stats['total']} = {acc:.1f}%")

    # Generate report
    generate_report(results, overall_accuracy, domain_stats)
    return overall_accuracy, results


def generate_report(results, overall_accuracy, domain_stats):
    os.makedirs("evaluation/results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    correct_results = [r for r in results if r["correct"]]
    wrong_results = [r for r in results if not r["correct"]]
    avg_latency = sum(r["total_ms"] for r in results) / len(results)

    lines = [
        "# Routing Benchmark Report",
        f"\nGenerated: {timestamp}",
        f"\n## Overall Results",
        f"\n| Metric | Value |",
        f"|--------|-------|",
        f"| Overall accuracy | {overall_accuracy:.1f}% ({sum(1 for r in results if r['correct'])}/{len(results)}) |",
        f"| Average latency | {avg_latency:.0f}ms per query |",
        f"\n## Per-Domain Accuracy",
        f"\n| Domain | Correct | Total | Accuracy |",
        f"|--------|---------|-------|----------|"]
    
    for domain, stats in domain_stats.items():
        acc = stats["correct"] / stats["total"] * 100
        lines.append(f"| {domain} | {stats['correct']} | {stats['total']} | {acc:.1f}% |")

    lines += [
        f"\n## Correctly Routed ({len(correct_results)})",
        f"\n| Query | Expected | Got | Latency |",
        f"|-------|----------|-----|---------|"]
    
    for r in correct_results:
        lines.append(f"| {r['query'][:50]} | {r['expected']} | {r['predicted']} | {r['total_ms']}ms |")

    if wrong_results:
        lines += [
            f"\n## Misrouted ({len(wrong_results)})",
            f"\n| Query | Expected | Got | Sub-queries |",
            f"|-------|----------|-----|-------------|"]
        
        for r in wrong_results:
            sq = "; ".join(r["sub_queries"])[:80]
            lines.append(f"| {r['query'][:50]} | {r['expected']} | {r['predicted']} | {sq} |")

    lines += [
        f"\n## Design Notes",
        f"\n- Routing uses semantic embedding similarity (FAISS cosine) — no LLM call",
        f"- Query rewriting decomposes ambiguous queries into specific sub-queries first",
        f"- Route ms is typically under 50ms — pure local vector math",
        f"- Misrouted queries are candidates for domain description tuning"]

    report = "\n".join(lines)
    with open("evaluation/results/routing_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport saved to evaluation/results/routing_report.md")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
