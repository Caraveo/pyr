#!/usr/bin/env python3
"""
Web search utilities for the AI agent.
Uses DuckDuckGo for free, no-API-key web search.
"""

import sys
from typing import List, Dict, Optional


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
        # Try to import duckduckgo-search
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            print("Warning: duckduckgo-search not installed. Install with: pip3 install duckduckgo-search", file=sys.stderr)
            return None
        
        results = []
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

