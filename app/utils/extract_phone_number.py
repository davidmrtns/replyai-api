import re


def extract_phone_number(text: str) -> str | None:
    """
    Extracts a phone number with 13 digits from the given text.
    """
    match = re.search(r"\d{13}", text)
    return match.group(0) if match else None
