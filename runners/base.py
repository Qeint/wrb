"""Base runner interface for WRB. Any web tool can implement this."""

class Runner:
    """Subclass this and implement the three methods."""
    name = "base"

    def fetch(self, url, max_chars=5000):
        """Fetch a URL and return its content.
        
        Returns:
            dict with keys:
                success: bool - did the tool report success?
                content: str - the page content (markdown or text)
                latency_ms: int - time to complete in milliseconds
                tokens: int - approximate token count of content
                (optional) tier: str - which tier was used (http, browser, etc.)
        """
        raise NotImplementedError

    def search(self, query, max_results=10):
        """Search for a query and return results.
        
        Returns:
            dict with keys:
                success: bool - did the tool report success?
                results: list of dicts with keys:
                    title: str
                    url: str
                    snippet: str
                latency_ms: int - time to complete in milliseconds
                tokens: int - approximate token count of all results combined
        """
        raise NotImplementedError

    def crawl(self, seed_url, focus, max_pages=30):
        """Crawl a site from a seed URL with a focus topic.
        
        Returns:
            dict with keys:
                success: bool - did the tool report success?
                pages: list of dicts with keys:
                    url: str
                    title: str
                    content: str (optional)
                latency_ms: int - time to complete in milliseconds
                tokens: int - approximate token count of all pages combined
        """
        raise NotImplementedError
