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

def _change_with_punctuation_or_accent_only(s):
    match = re.search(r'"(.+?)" was changed to "(.+?)"', s)
    if match:
        x, y = match.groups()
        x_clean = unidecode(x).translate(str.maketrans("", "", string.punctuation)).lower()
        y_clean = unidecode(y).translate(str.maketrans("", "", string.punctuation)).lower()
        return x_clean != y_clean
    return True

def validate_correction_explanations(correction_explanations: list[str]) -> str:
    logger.debug("Parsing correction explanations")
    correction_explanations = [y.split("|")[1].lstrip().rstrip(".") for x in correction_explanations for y in x.split("\n") if "|" in y]
    phrases_to_check = [
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
    def make_check(phrase):
        return lambda x: phrase not in x.lower()
    named_checks = [("Does not contain '" + phrase + "'", make_check(phrase)) for phrase in phrases_to_check]
    named_checks.append(("Change with punctuation or accent only", _change_with_punctuation_or_accent_only))
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
    return correction_explanation