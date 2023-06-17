import re


def split_by_delimiters(text: str, delimiters: list[str]) -> list[str]:
    regexPattern = "|".join(map(re.escape, delimiters))
    pieces = re.split(regexPattern, text)
    return pieces


def split_by_uppercase(text: str) -> list[str]:
    return re.split("(?<=[a-z])(?=[A-Z])", text)


with open("conversation_topics.txt", "r", encoding="utf-8") as fh:
    content = fh.read()
    delimiters = ["\n", "•", "→", " - ", "|"]
    pieces = split_by_delimiters(content, delimiters)
    pieces = [stripped for piece in pieces if (stripped := piece.strip())]
    allah_piece = next(piece for piece in pieces if piece.startswith("AllahBelief"))
    acosmism_piece = next(
        piece for piece in pieces if piece.startswith("AcosmismAgnosticism")
    )
    pieces.remove(allah_piece)
    pieces.remove(acosmism_piece)
    allah_pieces = split_by_uppercase(allah_piece)
    acosmism_pieces = split_by_uppercase(acosmism_piece)
    pieces.extend(allah_pieces)
    pieces.extend(acosmism_pieces)

    with open("conversation_topics_parsed.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(pieces))
