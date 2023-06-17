import logging
import os
import random

from dotenv import load_dotenv
import gradio
import openai

from orig_handler import call_api

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG
)
logger = logging.getLogger()

load_dotenv()

def check_api_key():
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if openai.api_key is None:
        print("You don't seem to have the OpenAI API key set up.")
        print("Please get your OpenAI API key from https://platform.openai.com/account/api-keys")
        api_key = input("Enter your OpenAI API key: ").strip()
        if api_key:
            with open(".env", "a") as f:
                f.write(f"OPENAI_API_KEY={api_key}\n")
            openai.api_key = api_key
            print("API key saved successfully.")
        else:
            print("No API key provided. The program will now exit.")
            exit()

check_api_key()

COST_PER_1K_TOKENS = 0.002 # USD
PROMPT_CONVERSATION_STARTER = open("prompts/conversation_starter.txt", "r").read()
PROMPT_SYSTEM_MAIN = open("prompts/system_main.txt", "r").read()

main_message_history = [
    {"role": "system", "content": PROMPT_SYSTEM_MAIN},
]
total_tokens_used = 0

def conversation_topic():
    with open("conversation_topics_parsed.txt", "r", encoding="utf-8") as file:
        lines = file.readlines()
    return random.choice(lines).strip() # Use strip() to remove the newline character at the end

def conversation_starter(conversation_topic):
    global total_tokens_used
    logger.info(f"Making request for conversation starter about topic `{conversation_topic}`...")
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": PROMPT_SYSTEM_MAIN},
            {"role": "user", "content": PROMPT_CONVERSATION_STARTER.format(conversation_topic)}
        ],
        temperature=0.8,
    )
    conversation_starter = completion.choices[0].message.content
    logger.debug(f"Received conversation starter `{conversation_starter}`")
    main_message_history.append({"role": "assistant", "content": conversation_starter})
    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used
    return conversation_starter

def accountant_message(total_tokens_used):
    return f"You've spent ${COST_PER_1K_TOKENS * total_tokens_used / 1000:.3f} USD on this conversation."

def chat(user_input):
    global main_message_history
    global total_tokens_used
    logger.info("Chat initiated by user...")
    correction_message, response_message, main_message_history, total_tokens_used = call_api(user_input, main_message_history, total_tokens_used)
    return correction_message, response_message, accountant_message(total_tokens_used)

conversation_topic = conversation_topic()
conversation_starter = conversation_starter(conversation_topic)

demo = gradio.Interface(
    fn=chat,
    inputs=gradio.inputs.Textbox(label="User input", lines=2, placeholder="Say something..."),
    outputs=[
        gradio.outputs.Textbox(label="Correction"),
        gradio.outputs.Textbox(label="Response"),
        gradio.outputs.Textbox(label="Accountant")
    ],
    title="Spanish Language Tutor",
    description=f"<b>A Spanish language tutor powered by GPT3.5</b>.<br><br>Your conversation topic is: <b>{conversation_topic}</b>. Your conversation starter is...<br><br>\"{conversation_starter}\"",
)

demo.launch()