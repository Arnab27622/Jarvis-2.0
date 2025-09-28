import sys
from g4f.client import Client
from assistant.core.speak_selector import speak
import strip_markdown
from assistant.activities.activity_monitor import record_user_activity
from assistant.automation.features.save_data_locally import (
    qa_lock,
    qa_file_path,
    qa_dict,
    save_qa_data,
)


def llm1(user_input):
    record_user_activity()

    client = Client()
    system_prompt = (
        "You are Jarvis, a helpful AI assistant for a programmer. "
        "Your creator is Arnab Dey. Arnab Dey is the only one to use you. "
        "Provide concise, accurate answers to questions. "
        "You answer questions, no matter how long, very quickly with low latency."
    )
    conversation_history = [{"role": "system", "content": system_prompt}]

    conversation_history.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="deepseek-v3",
        messages=conversation_history,
        web_search=True,
    )

    assistant_reply = strip_markdown.strip_markdown(
        response.choices[0].message.content.strip()
    )

    conversation_history.append({"role": "assistant", "content": assistant_reply})

    speak(assistant_reply)

    with qa_lock:
        qa_dict[user_input] = assistant_reply
        save_qa_data(qa_file_path, qa_dict)


if __name__ == "__main__":
    while True:
        user_input = input()

        if user_input == "exit":
            sys.exit()
        else:
            llm1(user_input=user_input)
