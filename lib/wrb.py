#!/usr/bin/env python3
"""
WRB - Web Research Benchmark
A tool-level benchmark for fetch, search, and crawl operations.
No LLM required. Any web tool can participate by implementing the runner interface.
"""

import json
import os
import sys
import time
import importlib
import argparse
from pathlib import Path

TASKS_DIR = Path(__file__).parent.parent / "tasks"

def load_tasks(name):
    p = TASKS_DIR / f"{name}.json"
    with open(p) as f:
        return json.load(f)["tasks"]

def count_tokens(text):
    """Approximate token count. chars/4 is a standard heuristic."""
    if not text:
        return 0
    return max(1, len(text) // 4)

def percentile(values, p):
    if not values:
        return 0
    s = sorted(values)
    idx = int(len(s) * p / 100)
    idx = min(idx, len(s) - 1)
    return s[idx]

# ============================================================
# FETCH BENCHMARK
# ============================================================

def run_fetch_bench(runner, tasks, verbose=False):
    results = []
    for i, task in enumerate(tasks):
        url = task["url"]
        tier = task["tier"]
        probe = task["probe"]
        category = task["category"]

        if verbose:
            print(f"  [{i+1}/{len(tasks)}] T{tier} {category:15s} {url[:65]}", end=" ", flush=True)

        try:
            res = runner.fetch(url, max_chars=5000)
        except Exception as e:
            res = {"success": False, "content": "", "latency_ms": 0, "error": str(e)}

        content = res.get("content", "")
        latency = res.get("latency_ms", 0)
        success = res.get("success", False)
        tokens = res.get("tokens", count_tokens(content))

        # Content retrieval: does the probe appear in the content?
        probe_found = probe.lower() in content.lower() if content else False

        # Honesty: if the tool claims success, did it actually get content?
        # false_positive = tool says success but probe not found
        # true_positive = tool says success and probe found
        # true_negative = tool says failure and probe not found
        # false_negative = tool says failure but probe found (rare)
        if success and not probe_found:
            honesty = "false_positive"
        elif success and probe_found:
            honesty = "true_positive"
        elif not success and not probe_found:
            honesty = "true_negative"
        else:
            honesty = "false_negative"

        result = {
            "url": url,
            "tier": tier,
            "category": category,
            "probe": probe,
            "probe_found": probe_found,
            "success": success,
            "honesty": honesty,
            "latency_ms": latency,
            "tokens": tokens,
            "content_len": len(content) if content else 0,
        }
        results.append(result)

        if verbose:
            status = "OK" if probe_found else "MISS"
            print(f"{status:4s} ({latency:5d}ms) {honesty}")

    return results

def score_fetch(results):
    total = len(results)
    if total == 0:
        return {}

    tiers = {1: [], 2: [], 3: []}
    for r in results:
        if r["tier"] in tiers:
            tiers[r["tier"]].append(r)

    # Per-tier retrieval rates
    tier_rates = {}
    for tier, tier_results in tiers.items():
        if tier_results:
            found = sum(1 for r in tier_results if r["probe_found"])
            tier_rates[tier] = found / len(tier_results)

    # Overall retrieval
    total_found = sum(1 for r in results if r["probe_found"])

    # Stealth score: tier-weighted (T3 counts 3x, T2 counts 2x, T1 counts 1x)
    weighted_total = 0
    weighted_found = 0
    for r in results:
        weight = r["tier"]
        weighted_total += weight
        if r["probe_found"]:
            weighted_found += weight
    stealth_score = weighted_found / weighted_total if weighted_total else 0

    # Speed (only successful fetches)
    success_latencies = [r["latency_ms"] for r in results if r["probe_found"]]
    all_latencies = [r["latency_ms"] for r in results]

    # Token efficiency (only successful fetches)
    success_tokens = [r["tokens"] for r in results if r["probe_found"]]

    # Honesty
    fp = sum(1 for r in results if r["honesty"] == "false_positive")
    tp = sum(1 for r in results if r["honesty"] == "true_positive")
    tn = sum(1 for r in results if r["honesty"] == "true_negative")
    fn = sum(1 for r in results if r["honesty"] == "false_negative")

    return {
        "total": total,
        "content_retrieved": total_found,
        "retrieval_rate": total_found / total,
        "tier_rates": tier_rates,
        "stealth_score": stealth_score,
        "speed_median_ms": percentile(success_latencies, 50) if success_latencies else 0,
        "speed_p90_ms": percentile(success_latencies, 90) if success_latencies else 0,
        "speed_median_all_ms": percentile(all_latencies, 50) if all_latencies else 0,
        "token_median": percentile(success_tokens, 50) if success_tokens else 0,
        "honesty": {
            "true_positive": tp,
            "false_positive": fp,
            "true_negative": tn,
            "false_negative": fn,
            "false_positive_rate": fp / (fp + tp) if (fp + tp) else 0,
        },
    }

# ============================================================
# SEARCH BENCHMARK
# ============================================================

def run_search_bench(runner, tasks, verbose=False):
    results = []
    for i, task in enumerate(tasks):
        query = task["query"]
        niche = task["niche"]
        expected_domains = task["expected_domains"]
        answer_snippets = task["answer_snippets"]

        if verbose:
            print(f"  [{i+1}/{len(tasks)}] {niche:15s} {query[:55]}", end=" ", flush=True)

        try:
            res = runner.search(query, max_results=10)
        except Exception as e:
            res = {"success": False, "results": [], "latency_ms": 0, "error": str(e)}

        results_list = res.get("results", [])
        latency = res.get("latency_ms", 0)
        tokens = res.get("tokens", 0)
        success = res.get("success", False)

        # Recall: did any expected domain appear in top 5?
        top5 = results_list[:5]
        domains_found = set()
        for r in top5:
            url = r.get("url", "")
            for domain in expected_domains:
                if domain in url:
                    domains_found.add(domain)
        recall = len(domains_found) / len(expected_domains) if expected_domains else 0
        domain_hit = len(domains_found) > 0

        # Precision: did any answer snippet appear in any result title or snippet?
        all_text = " ".join(
            r.get("title", "") + " " + r.get("snippet", "")
            for r in results_list
        ).lower()
        snippet_hit = any(s.lower() in all_text for s in answer_snippets)

        # Coverage: did the tool return any results?
        coverage = len(results_list) > 0

        result = {
            "query": query,
            "niche": niche,
            "recall": recall,
            "domain_hit": domain_hit,
            "snippet_hit": snippet_hit,
            "coverage": coverage,
            "latency_ms": latency,
            "tokens": tokens,
            "num_results": len(results_list),
        }
        results.append(result)

        if verbose:
            status = "OK" if snippet_hit else "MISS"
            print(f"{status:4s} recall={recall:.1f} results={len(results_list)}")

        time.sleep(0.5)

    return results

def score_search(results):
    total = len(results)
    if total == 0:
        return {}

    return {
        "total": total,
        "recall": sum(r["domain_hit"] for r in results) / total,
        "precision": sum(r["snippet_hit"] for r in results) / total,
        "coverage": sum(r["coverage"] for r in results) / total,
        "speed_median_ms": percentile([r["latency_ms"] for r in results], 50),
        "speed_p90_ms": percentile([r["latency_ms"] for r in results], 90),
        "token_median": percentile([r["tokens"] for r in results], 50),
    }

# ============================================================
# CRAWL BENCHMARK
# ============================================================

def run_crawl_bench(runner, tasks, verbose=False):
    results = []
    for i, task in enumerate(tasks):
        seed = task["seed_url"]
        focus = task["focus"]
        max_pages = task["max_pages"]
        known = set(task["known_relevant"])

        if verbose:
            print(f"  [{i+1}/{len(tasks)}] focus={focus:12s} seed={seed[:50]}", end=" ", flush=True)

        try:
            res = runner.crawl(seed, focus, max_pages=max_pages)
        except Exception as e:
            res = {"success": False, "pages": [], "latency_ms": 0, "error": str(e)}

        pages = res.get("pages", [])
        latency = res.get("latency_ms", 0)
        tokens = res.get("tokens", 0)

        # Coverage: fraction of known-relevant URLs found
        found_urls = set(p.get("url", "") for p in pages)
        known_found = known & found_urls
        coverage = len(known_found) / len(known) if known else 0

        # Precision: fraction of crawled pages that were relevant (focus in title or URL)
        relevant_pages = sum(
            1 for p in pages
            if focus.lower() in (p.get("title", "") + " " + p.get("url", "")).lower()
        )
        precision = relevant_pages / len(pages) if pages else 0

        result = {
            "seed_url": seed,
            "focus": focus,
            "pages_crawled": len(pages),
            "known_relevant_total": len(known),
            "known_relevant_found": len(known_found),
            "coverage": coverage,
            "precision": precision,
            "latency_ms": latency,
            "tokens": tokens,
            "found_urls": sorted(known_found),
            "missed_urls": sorted(known - found_urls),
        }
        results.append(result)

        if verbose:
            print(f"cov={coverage:.1%} prec={precision:.1%} pages={len(pages)} ({latency}ms)")

    return results

def score_crawl(results):
    if not results:
        return {}

    return {
        "total": len(results),
        "coverage": sum(r["coverage"] for r in results) / len(results),
        "precision": sum(r["precision"] for r in results) / len(results),
        "speed_total_ms": sum(r["latency_ms"] for r in results),
        "token_total": sum(r["tokens"] for r in results),
        "pages_crawled": sum(r["pages_crawled"] for r in results),
    }

# ============================================================
# REPORT
# ============================================================

def print_report(fetch_score, search_score, crawl_score, fetch_results, search_results, crawl_results, tool_name):
    print("\n" + "=" * 60)
    print(f"  WRB RESULTS: {tool_name}")
    print("=" * 60)

    if fetch_score:
        print("\nFETCH")
        print(f"  Content retrieval:    {fetch_score['retrieval_rate']:.1%} ({fetch_score['content_retrieved']}/{fetch_score['total']})")
        for tier in [1, 2, 3]:
            rate = fetch_score["tier_rates"].get(tier, 0)
            print(f"  Tier {tier}:              {rate:.1%}")
        print(f"  Stealth score:        {fetch_score['stealth_score']:.1%} (tier-weighted)")
        print(f"  Speed (median):        {fetch_score['speed_median_ms']:.0f}ms (success only)")
        print(f"  Speed (P90):           {fetch_score['speed_p90_ms']:.0f}ms")
        print(f"  Token efficiency:      {fetch_score['token_median']:.0f} tokens/page (median)")
        h = fetch_score["honesty"]
        print(f"  Honesty:               {h['true_positive']} TP, {h['false_positive']} FP, {h['true_negative']} TN, {h['false_negative']} FN")
        print(f"  False positive rate:   {h['false_positive_rate']:.1%}")

    if search_score:
        print("\nSEARCH")
        print(f"  Recall (domain hit):  {search_score['recall']:.1%}")
        print(f"  Precision (answer):    {search_score['precision']:.1%}")
        print(f"  Coverage:              {search_score['coverage']:.1%}")
        print(f"  Speed (median):        {search_score['speed_median_ms']:.0f}ms")
        print(f"  Speed (P90):           {search_score['speed_p90_ms']:.0f}ms")
        print(f"  Token efficiency:      {search_score['token_median']:.0f} tokens/query (median)")

    if crawl_score:
        print("\nCRAWL")
        print(f"  Coverage:              {crawl_score['coverage']:.1%} (known-relevant found)")
        print(f"  Precision:             {crawl_score['precision']:.1%} (relevant pages)")
        print(f"  Pages crawled:         {crawl_score['pages_crawled']}")
        print(f"  Speed (total):         {crawl_score['speed_total_ms']:.0f}ms")
        print(f"  Token total:           {crawl_score['token_total']:.0f}")

    print("\n" + "=" * 60)

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="WRB - Web Research Benchmark")
    parser.add_argument("runner", help="Runner module name (e.g. donsetch)")
    parser.add_argument("--tool-name", default=None, help="Display name for the tool")
    parser.add_argument("--fetch-only", action="store_true", help="Run only fetch benchmark")
    parser.add_argument("--search-only", action="store_true", help="Run only search benchmark")
    parser.add_argument("--crawl-only", action="store_true", help="Run only crawl benchmark")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--output", "-o", default=None, help="Save results JSON to file")
    args = parser.parse_args()

    # Load runner
    sys.path.insert(0, str(Path(__file__).parent.parent / "runners"))
    runner_mod = importlib.import_module(args.runner)
    runner = runner_mod.Runner()
    tool_name = args.tool_name or getattr(runner, "name", args.runner)

    run_fetch = not (args.search_only or args.crawl_only)
    run_search = not (args.fetch_only or args.crawl_only)
    run_crawl = not (args.fetch_only or args.search_only)

    fetch_score = search_score = crawl_score = None
    fetch_results = search_results = crawl_results = []

    if run_fetch:
        print(f"\n{'='*60}\n  FETCH BENCHMARK\n{'='*60}")
        tasks = load_tasks("fetch")
        print(f"  {len(tasks)} URLs across 3 tiers")
        fetch_results = run_fetch_bench(runner, tasks, verbose=args.verbose)
        fetch_score = score_fetch(fetch_results)

    if run_search:
        print(f"\n{'='*60}\n  SEARCH BENCHMARK\n{'='*60}")
        tasks = load_tasks("search")
        print(f"  {len(tasks)} queries across 11 niches")
        search_results = run_search_bench(runner, tasks, verbose=args.verbose)
        search_score = score_search(search_results)

    if run_crawl:
        print(f"\n{'='*60}\n  CRAWL BENCHMARK\n{'='*60}")
        tasks = load_tasks("crawl")
        print(f"  {len(tasks)} crawl targets")
        crawl_results = run_crawl_bench(runner, tasks, verbose=args.verbose)
        crawl_score = score_crawl(crawl_results)

    print_report(fetch_score, search_score, crawl_score, fetch_results, search_results, crawl_results, tool_name)

    if args.output:
        output = {
            "tool": tool_name,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "fetch": {"score": fetch_score, "results": fetch_results} if fetch_score else None,
            "search": {"score": search_score, "results": search_results} if search_score else None,
            "crawl": {"score": crawl_score, "results": crawl_results} if crawl_score else None,
        }
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nResults saved to {args.output}")

if __name__ == "__main__":
    main()
