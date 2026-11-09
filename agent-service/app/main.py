import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .pdf_utils import extract_text_without_references
from .rag_pipeline import build_generation_graph, get_embeddings_client, get_llm_client, split_text, to_references
from .schemas import AskRequest, AskResponse, IngestResponse, RecommendedPaper
from .translator_client import detect_language, translate
from .vector_store import ensure_collection, insert_chunks, search_similar


if config.GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

embeddings = get_embeddings_client()
llm = get_llm_client()
graph = build_generation_graph(llm)
collection = ensure_collection(index_type="HNSW")


def _validate_domain(domain: str) -> None:
    if domain not in config.SUPPORTED_DOMAINS:
        raise HTTPException(status_code=400, detail=f"Unsupported domain '{domain}'. Use one of {sorted(config.SUPPORTED_DOMAINS)}")


def _validate_language(language: str) -> None:
    if language not in config.SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language '{language}'. Use one of {sorted(config.SUPPORTED_LANGUAGES)}")


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/ingest", response_model=IngestResponse)
async def ingest_paper(
    file: UploadFile = File(...),
    paper_title: str = Form(...),
    domain: str = Form(...),
    language: str = Form(...),
):
    _validate_domain(domain)
    _validate_language(language)
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    file_bytes = await file.read()
    text = extract_text_without_references(file_bytes)
    if not text:
        raise HTTPException(status_code=400, detail="No parseable text found in PDF")

    chunks = split_text(text)
    vectors = embeddings.embed_documents(chunks)
    inserted = insert_chunks(collection, paper_title=paper_title, domain=domain, language=language, chunks=chunks, embeddings=vectors)

    return IngestResponse(
        paper_title=paper_title,
        domain=domain,
        language=language,
        inserted_chunks=inserted,
    )


@app.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest):
    _validate_domain(payload.domain)

    source_language = payload.source_language or detect_language(payload.question)
    _validate_language(source_language)

    question_en = payload.question if source_language == "en" else translate(payload.question, source_language, "en")
    question_vector = embeddings.embed_query(question_en)
    search_results = search_similar(collection, query_embedding=question_vector, domain=payload.domain, top_k=config.TOP_K)
    retrieved_chunks = [r.text_chunk for r in search_results]

    state = graph.invoke(
        {
            "user_question": payload.question,
            "working_question_en": question_en,
            "retrieved_chunks": retrieved_chunks,
        }
    )
    answer_en = state.get("answer_en", "I could not generate an answer from the indexed context.")
    final_answer = answer_en if source_language == "en" else translate(answer_en, "en", source_language)

    references, recommended = to_references(search_results, limit=2)
    return AskResponse(
        answer=final_answer,
        language=source_language,
        recommended_papers=[RecommendedPaper(**item) for item in recommended],
        references=references,
    )
