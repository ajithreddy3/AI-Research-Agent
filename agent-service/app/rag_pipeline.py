from collections import Counter
from typing import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, StateGraph

from . import config
from .vector_store import SearchResult


class AgentState(TypedDict, total=False):
    user_question: str
    working_question_en: str
    retrieved_chunks: list[str]
    answer_en: str


def get_embeddings_client() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(model=config.GEMINI_EMB_MODEL)


def get_llm_client() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=config.GEMINI_LLM_MODEL, temperature=0)


def split_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_text(text)


def build_generation_graph(llm: ChatGoogleGenerativeAI):
    def retrieve_node(state: AgentState) -> AgentState:
        # Retrieval is done before graph execution; keep this node for explicit workflow shape.
        return state

    def generate_node(state: AgentState) -> AgentState:
        context = "\n\n".join(state.get("retrieved_chunks", []))
        prompt = (
            "You are a research assistant. Use only retrieved context.\n"
            "If context is insufficient, clearly say so.\n"
            "Provide a concise factual answer.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{state['working_question_en']}"
        )
        response = llm.invoke(prompt)
        state["answer_en"] = response.content
        return state

    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


def to_references(results: list[SearchResult], limit: int = 2) -> tuple[list[str], list[dict]]:
    papers = Counter([r.paper_title for r in results])
    top = papers.most_common(limit)
    references = [title for title, _ in top]
    recommended = []
    for title, _ in top:
        scores = [r.score for r in results if r.paper_title == title]
        recommended.append({"paper_title": title, "score": float(min(scores)) if scores else 0.0})
    return references, recommended
