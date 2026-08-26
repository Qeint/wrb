# WRB - Web Research Benchmark

A tool-level benchmark for fetch, search, and crawl operations. No LLM required. Any web tool can participate by implementing a thin runner adapter.

Existing benchmarks (SimpleQA, BrowseComp, DeepResearch Bench) test agents (LLM + tools + reasoning). WRB tests the tool layer directly: can your fetch tool get real content from anti-bot sites, can your search tool find the right results, can your crawl tool discover relevant pages. Pure string matching, no API keys, no models.

## How it works

Three test categories, each measuring multiple dimensions:

### Fetch (48 URLs, 3 difficulty tiers)

Tests whether a tool can retrieve real content from a URL. Each URL has a reference probe string that must appear in the returned content.

| Tier | Difficulty | Count | Examples |
|---|---|---|---|
| 1 | No anti-bot, static content | 19 | Wikipedia, arxiv, MDN, Python docs, RFCs, NASA |
| 2 | Mild protection or JS-dependent | 16 | Stack Overflow, GitHub, npm, PyPI, crates.io |
| 3 | Aggressive anti-bot | 13 | Cloudflare, Akamai, Datadome, PerimeterX protected sites |

**Metrics:**
- Content retrieval rate (per tier and overall)
- Stealth score (tier-weighted: T3 counts 3x, T2 2x, T1 1x)
- Speed (median, P90)
- Token efficiency (tokens per successful fetch)
- Honesty (false positive rate: does the tool claim success when it actually got a bot wall?)

### Search (55 queries, 11 niches)

Tests whether a tool can find relevant results. Each query has expected domains and answer snippets.

Niches: science, history, technology, geography, sports, entertainment, health, business, niche, programming, arts.

**Metrics:**
- Recall (expected domains in top 5 results)
- Precision (answer snippet appears in any result)
- Coverage (did the tool return any results)
- Speed, token efficiency

### Crawl (5 targets)

Tests whether a tool can crawl a site and find relevant pages for a topic. Each target has a seed URL, focus topic, and known-relevant URLs.

**Metrics:**
- Coverage (fraction of known-relevant URLs found)
- Precision (fraction of crawled pages relevant to the focus)
- Speed, token efficiency

## Quick start

```bash
# Clone
git clone https://github.com/dondai44423/wrb.git
cd wrb

# Run with DonSeTch (requires donsetch on PATH)
python3 lib/wrb.py donsetch --verbose --output results.json

# Run only fetch
python3 lib/wrb.py donsetch --fetch-only --verbose

# Run only search
python3 lib/wrb.py donsetch --search-only --verbose

# Run only crawl
python3 lib/wrb.py donsetch --crawl-only --verbose
```

## Add your tool

1. Copy `runners/template.py` to `runners/<your_tool>.py`
2. Implement `fetch()`, `search()`, and `crawl()` methods
3. Run: `python3 lib/wrb.py <your_tool> --verbose`

```python
class Runner(BaseRunner):
    name = "YourTool"

    def fetch(self, url, max_chars=5000):
        # Call your tool's fetch API/CLI
        return {"success": True, "content": "...", "latency_ms": 500, "tokens": 100}

    def search(self, query, max_results=10):
        # Call your tool's search API/CLI
        return {"success": True, "results": [{"title": "...", "url": "...", "snippet": "..."}],
                "latency_ms": 300, "tokens": 200}

    def crawl(self, seed_url, focus, max_pages=30):
        # Call your tool's crawl API/CLI
        return {"success": True, "pages": [{"url": "...", "title": "..."}],
                "latency_ms": 5000, "tokens": 1000}
```

## Fairness

- **No login-walled sites.** Every URL is publicly accessible.
- **No captcha-only sites.** Anti-bot sites may or may not show captchas depending on the tool's stealth.
- **Speed includes everything.** For cloud tools, network latency is real. For local tools, processing time is real. Both are real-world numbers.
- **Token counting uses chars/4.** No tokenizer dependency. Standard heuristic.
- **Versioned task sets.** When URLs go stale, a new version is released. Scores are only comparable within the same version.

## What WRB measures that others don't

1. **Honesty.** No other benchmark checks if a tool correctly reports its own failures. Returning a bot wall and calling it "success" is worse than honestly saying "blocked." WRB tracks false positives.
2. **Tier-weighted stealth.** Getting past Cloudflare counts more than getting past Wikipedia. Easy sites don't inflate your score.
3. **Token efficiency.** For AI agents, context window is the bottleneck. A tool that returns 50KB when 5KB suffices is wasting the agent's budget.
4. **Tool-level, not agent-level.** No LLM needed. Any fetch/search/crawl tool can participate. Apples-to-apples comparison.

## Example output

```
FETCH
  Content retrieval:    95.8% (46/48)
  Tier 1:               100%
  Tier 2:               100%
  Tier 3:               84.6%
  Stealth score:        93.3% (tier-weighted)
  Speed (median):       772ms
  Speed (P90):          5200ms
  Token efficiency:     1105 tokens/page
  Honesty:              46 TP, 0 FP, 2 TN, 0 FN
  False positive rate:  0.0%

SEARCH
  Recall (domain hit):  81.8%
  Precision (answer):   96.4%
  Coverage:             100%
  Speed (median):       1356ms
  Speed (P90):          2043ms
  Token efficiency:     802 tokens/query

CRAWL
  Coverage:             XX% (known-relevant found)
  Precision:             XX% (relevant pages)
  Pages crawled:         XX
  Speed (total):         XXXXXms
  Token total:           XXXXX
```

## License

MIT

## Origin

Created by the [DonSeTch](https://github.com/dondai44423/donsetch) project. DonSeTch is the first tool to run WRB. WRB is independent: any tool can run it by implementing a runner adapter.
