"""Record a real local PDF ingestion and grounded-answer workflow.

Install requirements-demo.txt and run `python scripts/record_demo.py` with the
frontend, agent, translator, and Milvus already running. No responses are mocked.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "demo"
TITLE = "Sample Paper: Evidence-Based Research Assistance"
QUESTION = "What are the three stages of the research assistant described in this paper?"


def make_sample_pdf():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "sample-paper.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setTitle(TITLE)
    pdf.setAuthor("Ajith Reddy")
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(48, 788, "Evidence-Based Research Assistance")
    pdf.setFont("Helvetica", 11)
    lines = [
        "Ajith Reddy - synthetic sample for a software demonstration",
        "This document is an illustrative input, not a published research study.",
        "",
        "A research assistant can answer questions using evidence from uploaded PDFs.",
        "The workflow has three stages: indexing, retrieval, and generation.",
        "",
        "1. Indexing: Extract the PDF text, split it into chunks, and create embeddings.",
        "Store each embedding with its source text and paper title in a vector database.",
        "",
        "2. Retrieval: Embed the question and search for passages with similar meaning.",
        "Filter by the selected domain so the answer uses relevant research passages.",
        "",
        "3. Generation: Supply the retrieved passages to a language model.",
        "The model should answer using those passages and acknowledge missing evidence.",
        "",
        "Paper titles shown with the answer help the reader trace the source evidence.",
        "References are excluded from indexing to reduce irrelevant search results.",
        "",
        "References",
        "Bibliography-only sentinel: this line must not be indexed.",
    ]
    text = pdf.beginText(48, 760)
    text.setLeading(22)
    for line in lines:
        text.textLine(line)
    pdf.drawText(text)
    pdf.save()
    return path


def main():
    sample = make_sample_pdf()
    for url in ("http://127.0.0.1:8080/healthz", "http://127.0.0.1:8501/_stcore/health"):
        with urlopen(url, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError("A required local service is not healthy")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True, slow_mo=350)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            record_video_dir=str(OUTPUT / "raw"),
            record_video_size={"width": 1440, "height": 1000},
            reduced_motion="reduce",
        )
        page = context.new_page()
        video = page.video
        succeeded = False
        try:
            page.goto("http://127.0.0.1:8501", wait_until="networkidle")
            page.get_by_role("heading", name="Research Assistant (Option 1)").wait_for()
            page.wait_for_timeout(2000)
            page.locator('input[type="file"]').set_input_files(str(sample))
            page.get_by_role("textbox", name="Paper title").fill(TITLE)
            page.wait_for_timeout(1500)
            page.get_by_role("button", name="Upload + Index", exact=True).click()
            page.get_by_text("Indexed successfully.", exact=True).wait_for(timeout=200000)
            page.wait_for_timeout(3000)
            page.get_by_role("tab", name="Ask Questions").click()
            page.get_by_role("textbox", name="Question", exact=True).fill(QUESTION)
            language = page.get_by_test_id("stSelectbox").filter(has_text="Question language (optional)")
            language.get_by_role("combobox").click()
            page.get_by_role("option", name="en", exact=True).click()
            page.wait_for_timeout(2000)
            page.get_by_role("button", name="Ask", exact=True).click()
            page.get_by_role("heading", name="Answer", exact=True).wait_for(timeout=180000)
            page.get_by_role("heading", name="Answer", exact=True).scroll_into_view_if_needed()
            page.wait_for_timeout(5000)
            answer = page.get_by_test_id("stMarkdownContainer").all_text_contents()
            visible_text = page.locator("body").inner_text()
            if not all(word in visible_text.lower() for word in ("indexing", "retrieval", "generation")):
                raise RuntimeError("Generated answer did not include the sample paper's three stages")
            page.screenshot(path=str(OUTPUT / "sample-answer.png"), full_page=True)
            (OUTPUT / "evidence.json").write_text(json.dumps({
                "recorded_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(),
                "author": "Ajith Reddy", "paper_title": TITLE, "question": QUESTION,
                "sample_type": "synthetic demonstration paper", "domain": "AI", "language": "en",
                "indexing": "UI reported Indexed successfully.",
                "answer_markdown": answer, "mocked_responses": False,
            }, indent=2), encoding="utf-8")
            succeeded = True
        finally:
            context.close()
            target = OUTPUT / ("sample-demo.webm" if succeeded else "failed-attempt.webm")
            video.save_as(str(target))
            video.delete()
            browser.close()
        print("Recording saved:", target.relative_to(ROOT))


if __name__ == "__main__":
    main()
