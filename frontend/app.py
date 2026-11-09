import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://agent-svc:8080").rstrip("/")
SUPPORTED_LANGUAGES = ["en", "es", "fr", "it"]
SUPPORTED_DOMAINS = ["AI", "Security", "Other"]


def show_response_body(response: requests.Response) -> None:
    try:
        st.json(response.json())
    except ValueError:
        st.code(response.text if response.text else "<empty response body>")

st.set_page_config(page_title="Option 1 Research Assistant", layout="wide")
st.title("Research Assistant (Option 1)")

tab_upload, tab_ask = st.tabs(["Upload Papers", "Ask Questions"])

with tab_upload:
    st.subheader("Upload and index one paper")
    with st.form("upload_form"):
        file = st.file_uploader("Paper PDF", type=["pdf"])
        paper_title = st.text_input("Paper title")
        domain = st.selectbox("Domain", SUPPORTED_DOMAINS, index=0)
        language = st.selectbox("Original language", SUPPORTED_LANGUAGES, index=0)
        submitted = st.form_submit_button("Upload + Index")

    if submitted:
        if not file or not paper_title.strip():
            st.error("Please provide both PDF and paper title.")
        else:
            files = {"file": (file.name, file.getvalue(), "application/pdf")}
            data = {
                "paper_title": paper_title.strip(),
                "domain": domain,
                "language": language,
            }
            response = requests.post(f"{AGENT_BASE_URL}/ingest", files=files, data=data, timeout=180)
            if response.ok:
                st.success("Indexed successfully.")
                show_response_body(response)
            else:
                st.error(f"Indexing failed: {response.status_code}")
                show_response_body(response)

with tab_ask:
    st.subheader("Ask in English / Spanish / French / Italian")
    with st.form("ask_form"):
        question = st.text_area("Question", height=120)
        domain = st.selectbox("Domain to search", SUPPORTED_DOMAINS, index=0, key="ask_domain")
        source_language = st.selectbox("Question language (optional)", ["auto"] + SUPPORTED_LANGUAGES, index=0)
        ask_submitted = st.form_submit_button("Ask")

    if ask_submitted and question.strip():
        payload = {
            "question": question.strip(),
            "domain": domain,
            "source_language": None if source_language == "auto" else source_language,
        }
        response = requests.post(f"{AGENT_BASE_URL}/ask", json=payload, timeout=120)
        if response.ok:
            body = response.json()
            st.markdown("### Answer")
            st.write(body["answer"])
            st.markdown("### Recommended Papers")
            for paper in body.get("recommended_papers", []):
                st.write(f"- {paper['paper_title']} (score={paper['score']:.4f})")
            st.markdown("### References")
            for title in body.get("references", []):
                st.write(f"- {title}")
        else:
            st.error(f"Query failed: {response.status_code}")
            show_response_body(response)
