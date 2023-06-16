import json
import logging
import os
import random

from dotenv import load_dotenv
import gradio
import openai

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO
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
PROMPT_ANALYSE_CORRECTION = open("prompts/analyse_correction.txt", "r").read()
PROMPT_TRANSLATE_SENTENCE = open("prompts/translate_sentence.txt", "r").read()

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
            {"role": "user", "content": PROMPT_CONVERSATION_STARTER.format(conversation_topic)}
        ],
        temperature=0.8,
    )
    conversation_starter: str = completion.choices[0].message.content
    conversation_starter = conversation_starter.lstrip("A: ")
    logger.debug(f"Received conversation starter `{conversation_starter}`")
    main_message_history.append({"role": "assistant", "content": conversation_starter})
    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used
    return conversation_starter

def accountant_message(total_tokens_used):
    return f"You've spent ${COST_PER_1K_TOKENS * total_tokens_used / 1000:.3f} USD on this conversation."

def call_api(user_input):
    global total_tokens_used
    function_definition = {
        "name": "receive_outputs",
        "description": "A function that receives outputs",
        "parameters": {
            "type": "object",
            "properties": {
                "corrected_input": {
                    "type": "string",
                    "description": "A Spanish language correction of the user's input"
                },
                "corrections": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "A specific correction that was made to the user's input"
                    },
                    "description": "An exhaustive list of corrections made to the user's input"
                },
                "correction_explanations": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "An English language explanation of one specific correction made to the user's input"
                    },
                    "description": "An exhaustive list of corrections made to the user's input, with an explanation for each"
                },
                "conversation_response": {
                    "type": "string",
                    "description": "A Spanish language response to the user's input"
                }
            },
            "required": ["corrected_input", "correction_explanations", "conversation_response"]
        }
    }
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=[{"role": "user", "content": user_input}],
        functions=[function_definition  ],
        function_call={"name": "receive_outputs"},
        temperature=0.1
    )
    logger.debug(f"Received response for `{user_input}`")
    resp_dict = json.loads(completion.choices[0].message.to_dict()["function_call"]["arguments"])
    corrected_input = resp_dict["corrected_input"]
    explanations = "\n".join([f"{i}. {x}" for i, x in enumerate(resp_dict["correction_explanations"], 1)])
    correction_response = f"""Corrected input
---------------
{corrected_input}
"""
    if explanations:
        correction_response += f"""
Explanations
------------
{explanations}
"""
    conversation_response = resp_dict["conversation_response"]
    
    main_message_history.append({"role": "assistant", "content": conversation_response})
    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used
    return correction_response, conversation_response

def chat(user_input):
    logger.info("Chat initiated by user...")
    correction_message, response_message = call_api(user_input)
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