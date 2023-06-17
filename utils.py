import logging
import re
import string

from unidecode import unidecode

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG
)
logger = logging.getLogger()

PHRASES_TO_CHECK = [
    "¿",
    "¡",
    "accent",
    "bracket",
    "comma",
    "corrected sentence",
    "diacritic",
    "exclamation mark",
    "exclamation point",
    "no changes",
    "question mark",
    "the change"
]

def _check_closure(phrase):
    return lambda x: phrase not in x.lower()

def _change_with_punctuation_or_accent_only(s):
    match = re.search(r'"(.+?)" was changed to "(.+?)"', s)
    if match:
        x, y = match.groups()
        x_clean = unidecode(x).translate(str.maketrans("", "", string.punctuation)).lower()
        y_clean = unidecode(y).translate(str.maketrans("", "", string.punctuation)).lower()
        return x_clean != y_clean
    return True

named_checks = [("Does not contain '" + phrase + "'", _check_closure(phrase)) for phrase in PHRASES_TO_CHECK]
named_checks.append(("Change with punctuation or accent only", _change_with_punctuation_or_accent_only))

def validated_correction_explanation(correction_explanation: str) -> str:
    logger.debug(f"Parsing correction explanation `{correction_explanation}`")
    correction_explanation = correction_explanation.split("|")[1].strip(" .")
    
    logger.debug(f"Checking correction explanation `{correction_explanation}` for filter phrases")
    for name, check in named_checks:
        if not check(correction_explanation):
            logger.debug(f"Correction explanation `{correction_explanation}` fails check `{name}`")
            return ""
    else:
        logger.debug(f"Correction explanation `{correction_explanation}` passes all checks")
        return correction_explanation

def parse_correction_explanations(correction_explanations: list[str]) -> str:
    validated_correction_explanations = [validated_correction_explanation(y) for x in correction_explanations for y in x.split("\n") if "|" in y]
    validated_correction_explanations = [x for x in validated_correction_explanations if x]
    if len(validated_correction_explanations) == 0:
        return "No corrections made."
    elif len(validated_correction_explanations) == 1:
        return validated_correction_explanations[0]
    else:
        return "\n".join([f"{i}. {x}" for i, x in enumerate(validated_correction_explanations, 1)])