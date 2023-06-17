from concurrent.futures import ThreadPoolExecutor
import logging
import re

import openai

from utils import validate_correction_explanations

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG
)
logger = logging.getLogger()

PROMPT_ANALYSE_CORRECTION = open("prompts/analyse_correction.txt", "r").read()
PROMPT_TRANSLATE_SENTENCE = open("prompts/translate_sentence.txt", "r").read()

main_message_history = None
total_tokens_used = None

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

def call_api(user_input, _main_message_history, _total_tokens_used):
    global main_message_history
    global total_tokens_used
    main_message_history = _main_message_history
    total_tokens_used = _total_tokens_used
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
    
    validated_correction_explanation = validate_correction_explanations(correction_explanations)
    
    correction_response = "{correction}\n\n{explanation}".format(
        correction=" ".join(corrected_sentences),
        explanation=validated_correction_explanation
    )
    return correction_response, conversation_response, main_message_history, total_tokens_used