import requests

from . import config


def detect_language(text: str) -> str:
    response = requests.post(
        f"{config.TRANSLATOR_BASE_URL}/detect-language",
        json={"text": text},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["language"]


def translate(text: str, source_language: str, target_language: str) -> str:
    response = requests.post(
        f"{config.TRANSLATOR_BASE_URL}/translate",
        json={
            "text": text,
            "source_language": source_language,
            "target_language": target_language,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["translated_text"]
