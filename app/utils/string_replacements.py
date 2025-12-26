import re


REPLACEMENTS = {
    r"\bsr\.\b": "senhor",
    r"\bsra\.\b": "senhora",
    r"\bdr\.\b": "doutor",
    r"\bdra\.\b": "doutora",
    r"\b(\d{2}):(\d{2})\b": r"\1 horas e \2 minutos",
    r"\b(\d{2})/(\d{2})/(\d{4})\b": r"\1 de \2 de \3",  # TODO: for dates, replace the month number with the month name
}


def replace_abbreviations(message: str) -> str:
    for pattern, replacement in REPLACEMENTS.items():
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
    return message
