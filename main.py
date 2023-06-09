from concurrent.futures import ThreadPoolExecutor
import logging
import os
import re

from dotenv import load_dotenv
import gradio
import openai

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO)
logger = logging.getLogger()

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

COST_PER_1K_TOKENS = 0.002 # USD
PROMPT_SYSTEM_MAIN = open("prompts/system_main.txt", "r").read()
PROMPT_ANALYSE_CORRECTION = open("prompts/analyse_correction.txt", "r").read()
PROMPT_TRANSLATE_SENTENCE = open("prompts/translate_sentence.txt", "r").read()

main_message_history = [
    {"role": "system", "content": PROMPT_SYSTEM_MAIN}
]

total_tokens_used = 0

def accountant_message(total_tokens_used):
    return f"You've spent ${COST_PER_1K_TOKENS * total_tokens_used / 1000:.3f} USD on this conversation."

def get_response(user_input):
    global main_message_history
    global total_tokens_used
    main_message_history.append({"role": "user", "content": user_input})
    logger.info("Making request for main response...")
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=main_message_history
    )
    response = completion.choices[0].message.content
    main_message_history.append({"role": "assistant", "content": response})
    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used
    return response

def get_corrected_sentence(input_sentence):
    global total_tokens_used
    prompt = PROMPT_TRANSLATE_SENTENCE.format(sentence=input_sentence)
    logger.info("Making request for corrected sentence...")
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    corrected_sentence = completion.choices[0].message.content.replace("\"", "")
    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used
    return corrected_sentence

def get_correction_explanation(input_sentence, corrected_sentence):
    global total_tokens_used
    prompt = PROMPT_ANALYSE_CORRECTION.format(input_sentence=input_sentence, corrected_sentence=corrected_sentence)
    logger.info("Making request for correction explanation...")
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    correction_explanation = completion.choices[0].message.content
    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used
    return correction_explanation

def chat(user_input):
    logger.info("Chat initiated by user...")

    split_regex = r"(?<=[.!?])\s+"
    input_sentences = re.split(split_regex, user_input)
    
    with ThreadPoolExecutor() as executor:
        response_future = executor.submit(get_response, user_input)
        corrected_sentences_futures = [executor.submit(get_corrected_sentence, sentence) for sentence in input_sentences]
        
        response = response_future.result()
        corrected_sentences = [future.result() for future in corrected_sentences_futures]

        correction_explanations_futures = [executor.submit(get_correction_explanation, input_sentence, corrected_sentence) for input_sentence, corrected_sentence in zip(input_sentences, corrected_sentences)]
        correction_explanations = [future.result() for future in correction_explanations_futures]

    correction_explanations = [y.split("|")[1].lstrip().rstrip(".") for x in correction_explanations for y in x.split("\n") if "|" in y]
    checks = [
        lambda x: not x.startswith("No changes"),
        lambda x: not x.startswith("No other changes"),
        lambda x: "accent" not in x,
        lambda x: "brackets" not in x,
        lambda x: "exclamation mark" not in x,
        lambda x: "exclamation point" not in x,
        lambda x: "corrected sentence" not in x,
    ]
    correction_explanations = [x for x in correction_explanations if all([check(x) for check in checks])]
    correction_explanation = "\n".join([f"{i}. {x}" for i, x in enumerate(correction_explanations, 1)])

    correction_message = "{correction}\n\n{explanation}".format(
        correction=" ".join(corrected_sentences),
        explanation=correction_explanation
    )
    return correction_message, response, accountant_message(total_tokens_used)

demo = gradio.Interface(
    fn=chat,
    inputs=gradio.inputs.Textbox(label="User input", lines=2, placeholder="Say something..."),
    outputs=[
        gradio.outputs.Textbox(label="Correction"),
        gradio.outputs.Textbox(label="Response"),
        gradio.outputs.Textbox(label="Accountant")
    ],
    title="Spanish Language Tutor",
    description="A Spanish language tutor powered by GPT3.5.",
)

demo.launch()