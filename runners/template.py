#!/usr/bin/env python3
"""Runner template for WRB. Copy this file, rename it, and implement the three methods.

Usage:
  1. Copy this file to runners/<your_tool>.py
  2. Implement fetch(), search(), and crawl() methods
  3. Run: python3 lib/wrb.py <your_tool> --verbose
"""

import os
import time
from base import Runner as BaseRunner

class Runner(BaseRunner):
    name = "YourTool"

    def fetch(self, url, max_chars=5000):
        # Call your tool's fetch API/CLI here
        start = time.time()
        
        # Example: call your tool
        # content = your_tool.fetch(url)
        # success = your_tool.was_successful()
        # latency = int((time.time() - start) * 1000)
        
        content = ""  # replace with actual content
        success = False  # replace with actual status
        latency = int((time.time() - start) * 1000)
        tokens = max(1, len(content) // 4) if content else 0
        
        return {
            "success": success,
            "content": content,
            "latency_ms": latency,
            "tokens": tokens,
        }

    def search(self, query, max_results=10):
        # Call your tool's search API/CLI here
        start = time.time()
        
        results = []  # list of {title, url, snippet}
        latency = int((time.time() - start) * 1000)
        all_text = " ".join(r.get("title", "") + " " + r.get("snippet", "") for r in results)
        tokens = max(1, len(all_text) // 4) if all_text else 0
        
        return {
            "success": True,
            "results": results,
            "latency_ms": latency,
            "tokens": tokens,
        }

    def crawl(self, seed_url, focus, max_pages=30):
        # Call your tool's crawl API/CLI here
        start = time.time()
        
        pages = []  # list of {url, title}
        latency = int((time.time() - start) * 1000)
        tokens = 0  # approximate token count of all page content
        
        return {
            "success": True,
            "pages": pages,
            "latency_ms": latency,
            "tokens": tokens,
        }
