from fastapi import FastAPI, HTTPException
from googletrans import Translator
from pydantic import BaseModel, Field


SUPPORTED_LANGUAGES = {"en", "es", "fr", "it"}
translator = Translator()

app = FastAPI(title="Translator Service", version="1.0.0")


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source_language: str
    target_language: str


class TranslateResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str


class DetectLanguageRequest(BaseModel):
    text: str = Field(..., min_length=1)


class DetectLanguageResponse(BaseModel):
    language: str


def validate_language(language: str) -> None:
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language '{language}'. Allowed: {sorted(SUPPORTED_LANGUAGES)}",
        )


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/detect-language", response_model=DetectLanguageResponse)
async def detect_language(payload: DetectLanguageRequest):
    try:
        detection = translator.detect(payload.text)
        detected = detection.lang
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Translator backend detect failed: {exc}") from exc
    if detected not in SUPPORTED_LANGUAGES:
        return DetectLanguageResponse(language="en")
    return DetectLanguageResponse(language=detected)


@app.post("/translate", response_model=TranslateResponse)
async def translate(payload: TranslateRequest):
    validate_language(payload.source_language)
    validate_language(payload.target_language)
    if payload.source_language == payload.target_language:
        return TranslateResponse(
            translated_text=payload.text,
            source_language=payload.source_language,
            target_language=payload.target_language,
        )
    try:
        translated = translator.translate(
            payload.text,
            src=payload.source_language,
            dest=payload.target_language,
        ).text
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Translator backend translate failed: {exc}") from exc
    return TranslateResponse(
        translated_text=translated,
        source_language=payload.source_language,
        target_language=payload.target_language,
    )
