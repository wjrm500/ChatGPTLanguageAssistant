import json
import os

from dotenv import load_dotenv
import openai

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

COST_PER_1K_TOKENS = 0.002 # USD
SYSTEM_PROMPT = open("system_prompt.txt", "r").read()

message_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

total_tokens_used = 0

while True:
    user_input = input("User: ")
    message_history.append({"role": "user", "content": user_input})
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=message_history
    )
    assistant_output = completion.choices[0].message.content
    message_history.append({"role": "assistant", "content": assistant_output})
    print("Assistant:", assistant_output)

    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used
    print(f"Irritating accountant: You've spent ${COST_PER_1K_TOKENS * total_tokens_used / 1000:.3f} USD on this conversation.")