import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


SUPPORTED_LANGUAGES = {"en", "es", "fr", "it"}
SUPPORTED_DOMAINS = {"AI", "Security", "Other"}

APP_NAME = "Option1 LangGraph Agent"
APP_VERSION = "1.0.0"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "gemini-3-flash-preview")
GEMINI_EMB_MODEL = os.getenv("GEMINI_EMB_MODEL", "models/gemini-embedding-001")

TRANSLATOR_BASE_URL = os.getenv("TRANSLATOR_BASE_URL", "http://translator-svc:8000").rstrip("/")

MILVUS_HOST = os.getenv("MILVUS_HOST", "milvus-svc")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "paper_chunks")
MILVUS_USERNAME = os.getenv("MILVUS_USERNAME", "")
MILVUS_PASSWORD = os.getenv("MILVUS_PASSWORD", "")
MILVUS_METRIC_TYPE = "COSINE"
MILVUS_DIMENSION = int(os.getenv("MILVUS_DIMENSION", "3072"))

TOP_K = int(os.getenv("TOP_K", "4"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
