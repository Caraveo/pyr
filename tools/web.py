#!/usr/bin/env python3
"""
Web search utilities for the AI agent.
Uses DuckDuckGo for free, no-API-key web search.
"""

import sys
import warnings
from typing import List, Dict, Optional

# Suppress deprecation warnings for duckduckgo_search package
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*duckduckgo_search.*")


def search_web(query: str, max_results: int = 5) -> Optional[List[Dict[str, str]]]:
    """
    Search the web using DuckDuckGo.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
    
    Returns:
        List of dictionaries with 'title', 'url', and 'snippet' keys, or None if search fails
    """
    try:
        # Try to import ddgs (new package name, duckduckgo_search is deprecated)
        DDGS = None
        try:
            from ddgs import DDGS
        except ImportError:
            # Fallback to old package name for backwards compatibility
            try:
                import warnings
                # Suppress the deprecation warning BEFORE importing
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                warnings.filterwarnings("ignore", message=".*duckduckgo_search.*")
                from duckduckgo_search import DDGS
            except ImportError:
                print("Warning: ddgs not installed. Install with: pip3 install ddgs", file=sys.stderr)
                return None
        
        if DDGS is None:
            return None
        
        results = []
        # Suppress deprecation warnings when using the old package
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            warnings.filterwarnings("ignore", message=".*duckduckgo_search.*")
            with DDGS() as ddgs:
                # Search for the query
                search_results = ddgs.text(query, max_results=max_results)
                
                for result in search_results:
                    results.append({
                        'title': result.get('title', ''),
                        'url': result.get('href', ''),
                        'snippet': result.get('body', '')
                    })
        
        return results if results else None
        
    except Exception as e:
        print(f"Warning: Web search failed: {e}", file=sys.stderr)
        return None


def format_search_results(results: List[Dict[str, str]]) -> str:
    """
    Format search results as a string for inclusion in prompts.
    
    Args:
        results: List of search result dictionaries
    
    Returns:
        Formatted string with search results
    """
    if not results:
        return ""
    
    formatted = "\nWEB SEARCH RESULTS:\n"
    formatted += "=" * 80 + "\n"
    
    for i, result in enumerate(results, 1):
        formatted += f"\n[{i}] {result.get('title', 'No title')}\n"
        formatted += f"    URL: {result.get('url', 'No URL')}\n"
        formatted += f"    {result.get('snippet', 'No snippet')}\n"
    
    formatted += "=" * 80 + "\n"
    
    return formatted

