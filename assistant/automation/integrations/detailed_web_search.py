import os
import json
from groq import Groq
from serpapi import GoogleSearch
from dotenv import load_dotenv
from assistant.core.speak_selector import speak

load_dotenv()


def get_web_info(query, max_results=5, prints=False) -> str:
    """
    Uses SerpApi to perform a real-time Google search for the query.
    Returns JSON string of a list of dicts with keys: title, link, snippet.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise EnvironmentError("SERPAPI_API_KEY not set in environment variables.")

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": max_results,
    }

    search = GoogleSearch(params)
    results = search.get_dict()

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


def generate(user_prompt, system_prompt="Be Short and Concise", prints=False) -> str:
    """
    Generates a response to the user's prompt using the Groq API.
    Does a real-time web search when requested by calling get_web_info.
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

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set in environment variables.")

    groq_client = Groq(api_key=api_key)

    # Initial chat completion with tool call
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=function_descriptions,
        tool_choice="auto",
        max_tokens=4096,
    )

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

        # Call again with tool response for final completion
        second_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
        )
        res = second_response.choices[0].message.content
        speak(res)
    else:
        res = response_message.content
        speak(res)


if __name__ == "__main__":
    # Example usage
    prompt = "Search the web for Demon Slayer Infinity Castle Arc2 movie release date and features."
    generate(user_prompt=prompt, prints=True)
