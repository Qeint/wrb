#!/usr/bin/env python3
"""Verify candidate URLs by fetching each one and checking for real content.
Outputs verified URLs with reference snippets to tasks/verified.json"""

import json
import subprocess
import sys
import re
import time
import os

CANDIDATES = [
    # === TIER 1: No anti-bot, static content, extremely stable URLs ===
    # Wikipedia - I'm 100% confident about these URLs
    {"url": "https://en.wikipedia.org/wiki/Photosynthesis", "tier": 1, "category": "wikipedia", "probe": "Photosynthesis"},
    {"url": "https://en.wikipedia.org/wiki/Alan_Turing", "tier": 1, "category": "wikipedia", "probe": "Turing"},
    {"url": "https://en.wikipedia.org/wiki/World_War_II", "tier": 1, "category": "wikipedia", "probe": "World War"},
    {"url": "https://en.wikipedia.org/wiki/Python_(programming_language)", "tier": 1, "category": "wikipedia", "probe": "Python"},
    {"url": "https://en.wikipedia.org/wiki/Mitochondrion", "tier": 1, "category": "wikipedia", "probe": "mitochondrion"},
    {"url": "https://en.wikipedia.org/wiki/Goodfellas", "tier": 1, "category": "wikipedia", "probe": "Goodfellas"},
    {"url": "https://en.wikipedia.org/wiki/Mount_Everest", "tier": 1, "category": "wikipedia", "probe": "Everest"},
    {"url": "https://en.wikipedia.org/wiki/United_Nations", "tier": 1, "category": "wikipedia", "probe": "United Nations"},

    # arxiv - extremely stable
    {"url": "https://arxiv.org/abs/1706.03762", "tier": 1, "category": "arxiv", "probe": "Attention Is All You Need"},
    {"url": "https://arxiv.org/abs/1810.04805", "tier": 1, "category": "arxiv", "probe": "BERT"},
    {"url": "https://arxiv.org/abs/2005.14165", "tier": 1, "category": "arxiv", "probe": "GPT-3"},
    {"url": "https://arxiv.org/abs/2303.08774", "tier": 1, "category": "arxiv", "probe": "GPT-4"},

    # MDN - stable docs
    {"url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map", "tier": 1, "category": "mdn", "probe": "map"},
    {"url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Type", "tier": 1, "category": "mdn", "probe": "Content-Type"},

    # Python docs - stable
    {"url": "https://docs.python.org/3/library/http.server.html", "tier": 1, "category": "pythondocs", "probe": "HTTPServer"},
    {"url": "https://docs.python.org/3/library/json.html", "tier": 1, "category": "pythondocs", "probe": "json"},

    # RFC editor - stable
    {"url": "https://www.rfc-editor.org/rfc/rfc2616", "tier": 1, "category": "rfc", "probe": "Hypertext Transfer Protocol"},
    {"url": "https://www.rfc-editor.org/rfc/rfc793", "tier": 1, "category": "rfc", "probe": "Transmission Control Protocol"},

    # .gov - stable
    {"url": "https://www.nasa.gov/mission_pages/station/main/index.html", "tier": 1, "category": "gov", "probe": "Space Station"},

    # === TIER 2: Mild protection or JS-dependent, stable URLs ===
    # Stack Overflow - questions are extremely stable
    {"url": "https://stackoverflow.com/questions/11227809/why-is-processing-a-sorted-array-faster-than-processing-an-unsorted-array", "tier": 2, "category": "stackoverflow", "probe": "sorted array"},
    {"url": "https://stackoverflow.com/questions/231767/what-does-the-yield-keyword-do-in-python", "tier": 2, "category": "stackoverflow", "probe": "yield"},
    {"url": "https://stackoverflow.com/questions/9273580/how-do-i-undo-the-most-recent-local-commits-in-git", "tier": 2, "category": "stackoverflow", "probe": "git"},
    {"url": "https://stackoverflow.com/questions/5000648/what-is-the-difference-between-call-and-apply", "tier": 2, "category": "stackoverflow", "probe": "apply"},

    # GitHub repos - stable
    {"url": "https://github.com/rust-lang/rust", "tier": 2, "category": "github", "probe": "Rust"},
    {"url": "https://github.com/torvalds/linux", "tier": 2, "category": "github", "probe": "Linux"},
    {"url": "https://github.com/microsoft/vscode", "tier": 2, "category": "github", "probe": "Visual Studio Code"},
    {"url": "https://github.com/python/cpython", "tier": 2, "category": "github", "probe": "Python"},

    # npm packages - stable
    {"url": "https://www.npmjs.com/package/react", "tier": 2, "category": "npm", "probe": "React"},
    {"url": "https://www.npmjs.com/package/express", "tier": 2, "category": "npm", "probe": "Express"},
    {"url": "https://www.npmjs.com/package/typescript", "tier": 2, "category": "npm", "probe": "TypeScript"},

    # PyPI packages - stable
    {"url": "https://pypi.org/project/requests/", "tier": 2, "category": "pypi", "probe": "Requests"},
    {"url": "https://pypi.org/project/numpy/", "tier": 2, "category": "pypi", "probe": "NumPy"},
    {"url": "https://pypi.org/project/django/", "tier": 2, "category": "pypi", "probe": "Django"},

    # crates.io - stable
    {"url": "https://crates.io/crates/tokio", "tier": 2, "category": "crates", "probe": "Tokio"},
    {"url": "https://crates.io/crates/serde", "tier": 2, "category": "crates", "probe": "Serde"},

    # === TIER 3: Aggressive anti-bot protection ===
    # Crunchbase - PerimeterX, stable company pages, public content
    {"url": "https://www.crunchbase.com/organization/stripe", "tier": 3, "category": "perimeterx", "probe": "Stripe"},
    {"url": "https://www.crunchbase.com/organization/google", "tier": 3, "category": "perimeterx", "probe": "Google"},
    {"url": "https://www.crunchbase.com/organization/airbnb", "tier": 3, "category": "perimeterx", "probe": "Airbnb"},

    # CBS News - Cloudflare protected, stable article URLs (old news, stable)
    {"url": "https://www.cbsnews.com/news/50th-anniversary-apollo-11-moon-landing-photos/", "tier": 3, "category": "cloudflare", "probe": "Apollo"},

    # Discourse forum - Cloudflare protected (many are), try official ones
    {"url": "https://meta.discourse.org/t/what-is-discourse/2345", "tier": 3, "category": "cloudflare", "probe": "Discourse"},

    # Y Combinator news (Hacker News) - Cloudflare
    {"url": "https://news.ycombinator.com/item?id=1", "tier": 3, "category": "cloudflare", "probe": "Hacker News"},

    # Kayak - Akamai bot manager
    {"url": "https://www.kayak.com/flights", "tier": 3, "category": "akamai", "probe": "flight"},

    # Best Buy - Akamai
    {"url": "https://www.bestbuy.com/site/apple-airpods-pro-2nd-generation-with-usb-c-white/6455988.p", "tier": 3, "category": "akamai", "probe": "AirPods"},

    # Datadome-protected: Leboncoin (French classifieds)
    {"url": "https://www.leboncoin.fr/", "tier": 3, "category": "datadome", "probe": "leboncoin"},

    # == More Cloudflare-protected sites with real content ==
    # UK government - Cloudflare
    {"url": "https://www.gov.uk/browse/benefits", "tier": 3, "category": "cloudflare", "probe": "benefits"},

    # Bitdefender - Cloudflare
    {"url": "https://www.bitdefender.com/", "tier": 3, "category": "cloudflare", "probe": "Bitdefender"},

    # Discord - Cloudflare, has public pages
    {"url": "https://discord.com/safety", "tier": 3, "category": "cloudflare", "probe": "Discord"},
]

def fetch_url(url, timeout=30):
    """Fetch URL using donsetch and return (success, content, latency_ms)"""
    cmd = ["donsetch", "fetch", url, "--max-chars", "5000"]
    start = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "PATH": os.path.expanduser("~/.npm-global/bin:") + os.environ["PATH"]}
        )
        latency = int((time.time() - start) * 1000)
        content = result.stdout
        return True, content, latency
    except subprocess.TimeoutExpired:
        return False, "", int((time.time() - start) * 1000)
    except Exception as e:
        return False, str(e), int((time.time() - start) * 1000)

def check_probe(content, probe):
    """Check if probe string appears in content (case-insensitive)"""
    if not content:
        return False
    return probe.lower() in content.lower()

def main():
    verified = []
    failed = []

    print(f"Verifying {len(CANDIDATES)} candidate URLs...\n")

    for i, c in enumerate(CANDIDATES):
        url = c["url"]
        tier = c["tier"]
        probe = c["probe"]
        category = c["category"]

        print(f"[{i+1}/{len(CANDIDATES)}] T{tier} {category:15s} {url[:70]}...", end=" ")

        success, content, latency = fetch_url(url)

        if success and check_probe(content, probe):
            # Extract a more specific reference snippet from the content
            # Find the probe in context
            content_lower = content.lower()
            probe_lower = probe.lower()
            idx = content_lower.find(probe_lower)
            if idx >= 0:
                # Get 50 chars around the probe for a more specific reference
                start = max(0, idx - 20)
                end = min(len(content), idx + len(probe) + 30)
                snippet = content[start:end].strip()
                # Clean up
                snippet = re.sub(r'\s+', ' ', snippet)[:80]
            else:
                snippet = probe

            verified.append({
                "url": url,
                "tier": tier,
                "category": category,
                "probe": probe,
                "ref_snippet": snippet,
                "latency_ms": latency
            })
            print(f"OK  ({latency}ms)  ref: \"{snippet}\"")
        else:
            failed.append({"url": url, "tier": tier, "category": category, "reason": "probe not found" if success else "fetch failed"})
            print(f"FAIL ({latency}ms)")

        # Small delay to be nice
        time.sleep(0.3)

    print(f"\n=== RESULTS ===")
    print(f"Verified: {len(verified)}/{len(CANDIDATES)}")
    print(f"Failed:   {len(failed)}/{len(CANDIDATES)}")

    # Count per tier
    for tier in [1, 2, 3]:
        tier_verified = [v for v in verified if v["tier"] == tier]
        tier_total = [c for c in CANDIDATES if c["tier"] == tier]
        print(f"  Tier {tier}: {len(tier_verified)}/{len(tier_total)} verified")

    if failed:
        print("\nFailed URLs:")
        for f in failed:
            print(f"  T{f['tier']} {f['category']:15s} {f['url']}")

    # Save
    out_path = os.path.join(os.path.dirname(__file__), "..", "tasks", "verified.json")
    with open(out_path, "w") as f:
        json.dump({"verified": verified, "failed": failed}, f, indent=2)
    print(f"\nSaved to {out_path}")

if __name__ == "__main__":
    main()
