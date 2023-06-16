from concurrent.futures import ThreadPoolExecutor
import logging
import re
import string

import openai
from unidecode import unidecode

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO
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

def change_with_punctuation_or_accent_only(s):
    match = re.search(r'"(.+?)" was changed to "(.+?)"', s)
    if match:
        x, y = match.groups()
        x_clean = unidecode(x).translate(str.maketrans("", "", string.punctuation)).lower()
        y_clean = unidecode(y).translate(str.maketrans("", "", string.punctuation)).lower()
        return x_clean != y_clean
    return True

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

    logger.debug("Parsing correction explanations")
    correction_explanations = [y.split("|")[1].lstrip().rstrip(".") for x in correction_explanations for y in x.split("\n") if "|" in y]
    phrases_to_check = [
        "¿",
        "¡",
        "accent",
        "bracket",
        "change",
        "comma",
        "corrected sentence",
        "diacritic",
        "exclamation mark",
        "exclamation point",
        "question mark",
    ]
    named_checks = [("Does not contain '" + phrase + "'", lambda x: phrase not in x.lower()) for phrase in phrases_to_check]
    named_checks.append(("Change with punctuation or accent only", change_with_punctuation_or_accent_only))
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
    if len(validated_correction_explanations) == 0:
        correction_explanation = "No corrections made."
    elif len(validated_correction_explanations) == 1:
        correction_explanation = validated_correction_explanations[0]
    else:
        correction_explanation = "\n".join([f"{i}. {x}" for i, x in enumerate(validated_correction_explanations, 1)])
    correction_response = "{correction}\n\n{explanation}".format(
        correction=" ".join(corrected_sentences),
        explanation=correction_explanation
    )
    return correction_response, conversation_response, main_message_history, total_tokens_used