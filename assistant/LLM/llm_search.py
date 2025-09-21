import sys
from assistant.LLM.llm2 import llm2 as llm2_func
from assistant.LLM.llm1 import llm1 as llm1_func
from assistant.LLM.llm3 import llm3 as llm3_func


def llm_response(user_input: str) -> str:
    try:
        # Try llm3 first
        print("Using LLM3...")
        return llm3_func(user_input)
    except:
        # Fallback to llm2 on failure
        try:
            print(f"Using LLM2...")
            return llm2_func(user_input)
        except:
            # Fallback to llm1 on failure
            print("Using LLM1...")
            return llm1_func(user_input)


if __name__ == "__main__":
    while True:
        user_input = input()

        if user_input == "exit":
            sys.exit()
        else:
            llm_response(user_input=user_input)
