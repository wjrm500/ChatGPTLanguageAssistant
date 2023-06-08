import os

from dotenv import load_dotenv
import gradio
import openai

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

COST_PER_1K_TOKENS = 0.002 # USD
SYSTEM_PROMPT = open("system_prompt.txt", "r").read()

message_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

total_tokens_used = 0

def accountant_message(total_tokens_used):
    return f"You've spent ${COST_PER_1K_TOKENS * total_tokens_used / 1000:.3f} USD on this conversation."

def chat(user_input):
    global message_history
    global total_tokens_used

    message_history.append({"role": "user", "content": user_input})
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=message_history
    )
    assistant_output = completion.choices[0].message.content
    message_history.append({"role": "assistant", "content": assistant_output})

    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used

    return assistant_output, accountant_message(total_tokens_used)

demo = gradio.Interface(
    fn=chat,
    inputs=gradio.inputs.Textbox(label="User input", lines=2, placeholder="Say something..."),
    outputs=[
        gradio.outputs.Textbox(label="Assistant"),
        gradio.outputs.Textbox(label="Accountant")
    ],
    title="Spanish Language Tutor",
    description="A Spanish language tutor powered by GPT3.5.",
)

demo.launch()