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
    "question mark",
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

def validate_correction_explanation(correction_explanation: str) -> bool:
    logger.debug("Parsing correction explanation `{correction_explanation}`")
    correction_explanation = correction_explanation.split("|")[1].strip(" .")
    
    logger.debug(f"Checking correction explanation `{correction_explanation}` for filter phrases")
    for name, check in named_checks:
        if not check(correction_explanation):
            logger.debug(f"Correction explanation `{correction_explanation}` fails check `{name}`")
            return False
    else:
        logger.debug(f"Correction explanation `{correction_explanation}` passes all checks")
        return True

def parse_correction_explanations(correction_explanations: list[str]) -> str:
    validated_correction_explanations = [x for x in correction_explanations if validate_correction_explanation(x)]
    if len(validated_correction_explanations) == 0:
        return "No corrections made."
    elif len(validated_correction_explanations) == 1:
        return validated_correction_explanations[0]
    else:
        return "\n".join([f"{i}. {x}" for i, x in enumerate(validated_correction_explanations, 1)])