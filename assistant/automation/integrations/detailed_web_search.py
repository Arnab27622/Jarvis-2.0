"""
Module for performing real-time web searches and AI-driven response generation.
Integrates SerpApi for search data and Groq LLM for intelligent query processing.
"""

import json
from groq import Groq
from serpapi import GoogleSearch
from assistant.core.config import config
from assistant.core.speak_selector import speak
from assistant.core.llm_utils import clean_llm_output, save_to_brain
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
    except Exception as e:
        print(f"SerpApi Error: {e}")
        speak("I'm sorry, I encountered an error while searching the web.")
        return "[]"

    items = results.get("organic_results", [])

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


def generate(user_prompt: str, system_prompt: str = "Be Short and Concise", prints: bool = False) -> str:
    """
    Generates an AI response, optionally using web search tools if required.
    """
    function_descriptions = [
        {
            "type": "function",
            "function": {
                "name": "get_web_info",
                "description": "Gets real-time information about the query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to search on the web",
                        }
                    },
                    "required": ["query"],
                },
            },
        }
    ]

    if system_prompt == "Be Short and Concise":
        system_prompt = (
            "You are a helpful assistant with access to real-time web search. "
            "If the user asks for information you don't have or that requires a search, "
            "use the get_web_info tool. Do not explain your tool use. "
            "Respond in a concise, friendly manner."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    api_key = config.groq_api_key
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set in environment variables.")

    groq_client = Groq(api_key=api_key)

    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=function_descriptions,
            tool_choice="auto",
            max_tokens=4096,
            temperature=0,
        )
    except Exception as e:
        print(f"Groq API Error: {e}")
        speak("I had trouble connecting to my brain. Please check your internet connection.")
        return ""

    response_message = response.choices[0].message

    tool_calls = response_message.tool_calls

    if tool_calls:
        available_functions = {
            "get_web_info": get_web_info,
        }

        messages.append(response_message)

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            if function_name not in available_functions:
                continue
            function_args = json.loads(tool_call.function.arguments)
            function_response = available_functions[function_name](**function_args)
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )

        second_response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
        )
        res = second_response.choices[0].message.content
        clean_res = clean_llm_output(res)
        save_to_brain(user_prompt, clean_res)
        speak(clean_res)
    else:
        res = response_message.content
        clean_res = clean_llm_output(res)
        save_to_brain(user_prompt, clean_res)
        speak(clean_res)


if __name__ == "__main__":
    prompt = "Search the web for Demon Slayer Infinity Castle Arc2 movie release date and features."
    generate(user_prompt=prompt, prints=True)


@on_regex(r"search\s+(?:the\s+web\s+for\s+|web\s+for\s+|for\s+)?(?P<query>.*?)(?:\s+(?:on|in|from)\s+(?P<provider>google|youtube|wikipedia|wiki))?$", priority=2)
def handle_unified_search(query, provider=None):
    """
    Routes search requests to the appropriate provider based on user input.
    """
    p = (provider or "").lower()
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
    else:
        speak(f"Searching the web for {q}. Please wait a moment...")
        generate(user_prompt=q, prints=True)
