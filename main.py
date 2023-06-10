from concurrent.futures import ThreadPoolExecutor
import logging
import os
import re

from dotenv import load_dotenv
import gradio
import openai

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG
)
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

def get_conversation_response(user_input):
    global main_message_history
    global total_tokens_used
    main_message_history.append({"role": "user", "content": user_input})
    logger.info("Making request for conversation response...")
    logger.debug(f"Sending user input `{user_input}` for conversation response")
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=main_message_history
    )
    conversation_response = completion.choices[0].message.content
    logger.debug(f"Received conversation response `{conversation_response}` for `{user_input}`")
    main_message_history.append({"role": "assistant", "content": conversation_response})
    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used
    return conversation_response

def get_corrected_sentence(input_sentence):
    global total_tokens_used
    prompt = PROMPT_TRANSLATE_SENTENCE.format(sentence=input_sentence)
    logger.info("Making request for corrected sentence...")
    logger.debug(f"Sending input sentence `{input_sentence}` for correction")
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    corrected_sentence = completion.choices[0].message.content.replace("\"", "")
    logger.debug(f"Received corrected sentence `{corrected_sentence}` for `{input_sentence}`")
    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used
    return corrected_sentence

def get_correction_explanation(input_sentence, corrected_sentence):
    global total_tokens_used
    prompt = PROMPT_ANALYSE_CORRECTION.format(input_sentence=input_sentence, corrected_sentence=corrected_sentence)
    logger.info("Making request for correction explanation...")
    logger.debug(f"Sending input sentence `{input_sentence}` and corrected sentence `{corrected_sentence}` for correction explanation")
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    correction_explanation = completion.choices[0].message.content
    logger.debug(f"Received correction explanation `{correction_explanation}` for input sentence `{input_sentence}` and corrected sentence `{corrected_sentence}`")
    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used
    return correction_explanation

def chat(user_input):
    logger.info("Chat initiated by user...")

    split_regex = r"(?<=[.!?])\s+"
    input_sentences = re.split(split_regex, user_input)
    
    with ThreadPoolExecutor() as executor:
        conversation_response_future = executor.submit(get_conversation_response, user_input)
        corrected_sentences_futures = [executor.submit(get_corrected_sentence, sentence) for sentence in input_sentences]
        
        conversation_response = conversation_response_future.result()
        corrected_sentences = [future.result() for future in corrected_sentences_futures]

        correction_explanations_futures = [executor.submit(get_correction_explanation, input_sentence, corrected_sentence) for input_sentence, corrected_sentence in zip(input_sentences, corrected_sentences)]
        correction_explanations = [future.result() for future in correction_explanations_futures]

    logger.debug("Parsing correction explanations")
    correction_explanations = [y.split("|")[1].lstrip().rstrip(".") for x in correction_explanations for y in x.split("\n") if "|" in y]
    named_checks = [
        ("Does not start with 'No changes'", lambda x: not x.startswith("No changes")),
        ("Does not start with 'No other changes'", lambda x: not x.startswith("No other changes")),
        ("Does not contain 'accent'", lambda x: "accent" not in x),
        ("Does not contain 'brackets'", lambda x: "brackets" not in x),
        ("Does not contain 'exclamation mark'", lambda x: "exclamation mark" not in x),
        ("Does not contain 'exclamation point'", lambda x: "exclamation point" not in x),
        ("Does not contain 'corrected sentence'", lambda x: "corrected sentence" not in x),
    ]
    logger.debug("Checking correction explanations")
    validated_correction_explanations = []
    for i, correction_explanation in enumerate(correction_explanations, 1):
        logger.debug(f"Checking correction explanation {i}: `{correction_explanation}`")
        for name, check in named_checks:
            if not check(correction_explanation):
                logger.debug(f"Correction explanation {i} fails check `{name}`")
                break
        else:
            logger.debug(f"Correction explanation {i} passes all checks")
            validated_correction_explanations.append(correction_explanation)
    correction_explanation = "\n".join([f"{i}. {x}" for i, x in enumerate(validated_correction_explanations, 1)])

    correction_message = "{correction}\n\n{explanation}".format(
        correction=" ".join(corrected_sentences),
        explanation=correction_explanation
    )
    return correction_message, conversation_response, accountant_message(total_tokens_used)

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