def uppercase(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return text.upper()


def lowercase(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return text.lower()


def replace_text(text: str, old: str, new: str) -> str:
    if not all(isinstance(value, str) for value in (text, old, new)):
        raise TypeError("text, old, and new must be strings")
    return text.replace(old, new)
