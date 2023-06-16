import json
import logging

import openai

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO
)
logger = logging.getLogger()

def dedent_multiline_string(multiline_string):
    return "\n".join([line.lstrip() for line in multiline_string.split("\n")]).lstrip()

def call_api(user_input, main_message_history, total_tokens_used):
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
    correction_response = dedent_multiline_string(
        f"""
        Corrected input
        ---------------
        {corrected_input}
        """
    )
    if explanations:
        correction_response += dedent_multiline_string(
            f"""
            Explanations
            ------------
            {explanations}
            """
        )
    conversation_response = resp_dict["conversation_response"]
    
    main_message_history.append({"role": "assistant", "content": conversation_response})
    tokens_used = completion.usage.total_tokens
    total_tokens_used += tokens_used
    return correction_response, conversation_response, main_message_history, total_tokens_used