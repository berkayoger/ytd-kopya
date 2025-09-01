import re


def validate_password(pw: str) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if len(pw) < 10:
        errors.append("En az 10 karakter")
    if not re.search(r"[A-Z]", pw):
        errors.append("En az 1 büyük harf")
    if not re.search(r"[a-z]", pw):
        errors.append("En az 1 küçük harf")
    if not re.search(r"\d", pw):
        errors.append("En az 1 rakam")
    if not re.search(r"[^\w\s]", pw):
        errors.append("En az 1 sembol")
    return (len(errors) == 0, errors)
