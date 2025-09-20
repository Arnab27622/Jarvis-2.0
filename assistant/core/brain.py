from assistant.LLM.llm1 import (
    Client,
    strip_markdown as strip_markdown1,
)
from assistant.LLM.llm2 import llm2 as llm2_func
from assistant.core.speak_selector import speak


class LLM1Wrapper:
    def __init__(self):
        self.client = Client()
        self.system_prompt = (
            "You are Jarvis, a helpful AI assistant for a software engineer. "
            "Your creator is Arnab Dey. Arnab Dey is the only one to use you. "
            "Provide concise, accurate answers to questions. "
            "You answer questions, no matter how long, very quickly with low latency."
        )
        self.conversation_history = [{"role": "system", "content": self.system_prompt}]

    def ask(self, user_input):
        self.conversation_history.append({"role": "user", "content": user_input})
        response = self.client.chat.completions.create(
            model="deepseek-v3",
            messages=self.conversation_history,
            web_search=True,
        )
        assistant_reply = strip_markdown1.strip_markdown(
            response.choices[0].message.content.strip()
        )
        self.conversation_history.append(
            {"role": "assistant", "content": assistant_reply}
        )
        speak(assistant_reply)
        return assistant_reply


llm1_wrapper = LLM1Wrapper()


def brain(user_input: str) -> str:
    try:
        # Try llm1 first
        print("Using LLM1...")
        return llm1_wrapper.ask(user_input)
    except Exception as e:
        # Fallback to llm2 on failure
        print(f"Using LLM2...")
        return llm2_func(user_input)
