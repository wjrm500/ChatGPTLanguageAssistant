from concurrent.futures import ThreadPoolExecutor
import os
import re

from dotenv import load_dotenv
import gradio
import openai

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

def chat(user_input):
    global main_message_history
    global total_tokens_used

    split_regex = r"(?<=[.!?])\s+"
    input_sentences = re.split(split_regex, user_input)
    corrected_sentences = []
    for input_sentence in input_sentences:
        prompt = PROMPT_TRANSLATE_SENTENCE.format(sentence=input_sentence)
        print("Making request...")
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        ai_output = completion.choices[0].message.content.replace("\"", "")
        corrected_sentences.append(ai_output)
        tokens_used = completion.usage.total_tokens
        total_tokens_used += tokens_used
    
    correction_explanations = []
    for input_sentence, corrected_sentence in zip(input_sentences, corrected_sentences):
        prompt = PROMPT_ANALYSE_CORRECTION.format(input_sentence=input_sentence, corrected_sentence=corrected_sentence)
        print("Making request...")
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        ai_output = completion.choices[0].message.content
        correction_explanations.append(ai_output)
        tokens_used = completion.usage.total_tokens
        total_tokens_used += tokens_used
    correction_explanations = [y.split("|")[1].lstrip().rstrip(".") for x in correction_explanations for y in x.split("\n") if "|" in y]
    checks = [
        lambda x: not x.startswith("No changes"),
        lambda x: not x.startswith("No other changes"),
        lambda x: "accent" not in x,
        lambda x: "brackets" not in x,
        lambda x: "exclamation mark" not in x,
        lambda x: "exclamation point" not in x,
    ]
    correction_explanations = [x for x in correction_explanations if all([check(x) for check in checks])]
    correction_explanation = "\n".join([f"{i}. {x}" for i, x in enumerate(correction_explanations, 1)])

    main_message_history.append({"role": "user", "content": user_input})
    print("Making request...")
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=main_message_history
    )
    ai_output = completion.choices[0].message.content
    main_message_history.append({"role": "assistant", "content": ai_output})
    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used
    
    final_ai_output = """
Input
-----
{user_input}

Correction
----------
{correction}

Explanation of corrections
--------------------------
{explanation}

Response
--------
{response}
""".format(
    user_input=user_input,
    correction=" ".join(corrected_sentences),
    explanation=correction_explanation,
    response=ai_output
)
    return final_ai_output, accountant_message(total_tokens_used)

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