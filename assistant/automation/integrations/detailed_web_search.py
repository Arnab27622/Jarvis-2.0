"""
Module for performing real-time web searches and AI-driven response generation.
Integrates SerpApi for search data and Groq LLM for intelligent query processing.
"""

import json
from serpapi import GoogleSearch
from assistant.core.config import config
from assistant.core.speak_selector import speak
from assistant.automation.integrations.youtube_automation import search_on_youtube
from assistant.automation.integrations import wiki_search
from assistant.automation.integrations.google_search_automation import handle_web_search
from assistant.core.registry import on_regex


def get_web_info(query: str, max_results: int = 5, prints: bool = False) -> str:
    """
    Executes a Google search via SerpApi and returns structured results.
    """
    api_key = config.serpapi_api_key
    if not api_key:
        raise EnvironmentError("SERPAPI_API_KEY not set in environment variables.")

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": max_results,
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        if "error" in results:
            raise Exception(results["error"])
        items = results.get("organic_results", [])
    except Exception as e:
        print(f"SerpApi Error: {e}, falling back to DuckDuckGo...")
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=max_results))
                items = []
                for res in ddg_results:
                    items.append({
                        "title": res.get("title", ""),
                        "link": res.get("href", ""),
                        "snippet": res.get("body", "")
                    })
        except Exception as ddg_err:
            print(f"DDG Error: {ddg_err}")
            speak("I'm sorry, I encountered an error while searching the web.")
            return "[]"

    response = []
    for item in items:
        response.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
        )

    response_json = json.dumps(response)
    return response_json


@on_regex(r"search\s+(?:for\s+)?(?P<query>.+?)\s+(?:on|in|from)\s+(?P<provider>youtube|wikipedia|wiki|google)$", priority=2)
def handle_unified_search(query, provider):
    """
    Routes search requests to the appropriate provider based on user input.
    General 'search for X' commands are handled natively by the ResearcherAgent instead.
    """
    p = provider.lower()
    q = query.strip()

    if p == "youtube":
        speak(f"Searching for {q} on YouTube")
        search_on_youtube(q)
    elif p in ["wikipedia", "wiki"]:
        speak(f"Searching Wikipedia for {q}")
        wiki_search(q)
    elif p == "google":
        speak(f"Searching Google for {q}")
        handle_web_search(q)
