import os
import json
from groq import Groq
from serpapi import GoogleSearch
from dotenv import load_dotenv
from assistant.core.speak_selector import speak

# Load environment variables from .env file for secure API key storage
load_dotenv()


def get_web_info(query, max_results=5, prints=False) -> str:
    """
    Perform real-time Google search using SerpApi and return structured results.

    This function executes a web search through the SerpApi service, which provides
    access to real-time Google search results without the limitations of direct
    scraping. The results are structured and returned as JSON for easy processing.

    Args:
        query (str): The search query to execute on Google
        max_results (int): Maximum number of search results to return (default: 5)
        prints (bool): Debug flag to enable print statements (default: False)

    Returns:
        str: JSON string containing a list of search results. Each result includes:
            - title (str): The title of the search result
            - link (str): The URL of the search result
            - snippet (str): A brief description or excerpt from the page

    Raises:
        EnvironmentError: If SERPAPI_API_KEY environment variable is not set
        Exception: For network errors or API failures

    Example:
        >>> get_web_info("Python programming", 3)
        '[{"title": "Python Official Site", "link": "https://python.org", "snippet": "The official Python website..."}, ...]'

    Note:
        Requires a valid SerpApi API key set in the SERPAPI_API_KEY environment variable.
        SerpApi is a paid service that provides access to Google search results.
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
    Generate AI-powered responses with real-time web search capabilities.

    This function uses the Groq API with function calling to determine when
    real-time information is needed. It can automatically perform web searches
    and incorporate the results into its response generation.

    Process Flow:
        1. Initial request to Groq API with function definitions
        2. AI model decides if web search is needed
        3. If search needed: executes get_web_info function
        4. Second API call with search results for final response
        5. Response is spoken to the user

    Args:
        user_prompt (str): The user's question or request for information
        system_prompt (str): Instructions for the AI model's behavior (default: "Be Short and Concise")
        prints (bool): Debug flag to enable print statements (default: False)

    Returns:
        str: The final generated response from the AI model

    Raises:
        EnvironmentError: If GROQ_API_KEY environment variable is not set
        Exception: For API errors, network issues, or function execution failures

    Example:
        >>> generate("What's the latest news about AI?")
        # Performs web search and provides current information
        # Speaks: "According to recent reports..."

    Model Used:
        llama-3.3-70b-versatile: A powerful 70B parameter model optimized for
        versatile tasks including reasoning, coding, and instruction following.

    Note:
        Requires valid Groq API and SerpApi keys set in environment variables.
        The function calling capability allows the AI to autonomously decide
        when real-time information is necessary.
    """
    # Define the web search function that the AI can call
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

    # Initialize conversation with system instructions and user prompt
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set in environment variables.")

    groq_client = Groq(api_key=api_key)

    # Initial chat completion with tool call capability
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=function_descriptions,  # Enable function calling
        tool_choice="auto",  # Let the model decide if it needs to use the function
        max_tokens=4096,
    )

    response_message = response.choices[0].message

    # Check if the model wants to call the web search function
    tool_calls = response_message.tool_calls

    if tool_calls:
        # Map available functions for execution
        available_functions = {
            "get_web_info": get_web_info,
        }

        # Add the model's response (with tool calls) to the conversation history
        messages.append(response_message)

        # Execute each requested function call
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

        # Second API call with web search results included in context
        second_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
        )
        res = second_response.choices[0].message.content
        speak(res)
    else:
        # No web search needed - use the initial response
        res = response_message.content
        speak(res)


if __name__ == "__main__":
    """
    Demonstration and testing entry point for the web search system.

    When run as a standalone script, this demonstrates the integration of
    AI-powered response generation with real-time web search capabilities.

    Example:
        python detailed_web_search.py
        # Will search for Demon Slayer information and speak the results
    """
    # Example usage - search for current movie information
    prompt = "Search the web for Demon Slayer Infinity Castle Arc2 movie release date and features."
    generate(user_prompt=prompt, prints=True)
