from g4f.client import Client
from assistant.core.speak_selector import speak
import strip_markdown


def llm1():
    client = Client()
    system_prompt = (
        "You are Jarvis, a helpful AI assistant for a software engineer. "
        "Your creator is Arnab Dey. Arnab Dey is the only one to use you. "
        "Provide concise, accurate answers to questions. "
        "You answer questions, no matter how long, very quickly with low latency."
    )
    conversation_history = [{"role": "system", "content": system_prompt}]

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting chat...")
            break

        conversation_history.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model="deepseek-v3",
            messages=conversation_history,
            web_search=True,
        )

        assistant_reply = strip_markdown.strip_markdown(
            response.choices[0].message.content.strip()
        )

        # speak(assistant_reply)

        conversation_history.append({"role": "assistant", "content": assistant_reply})


if __name__ == "__main__":
    llm1()
