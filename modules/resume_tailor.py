"""
Resume Tailoring Module
=======================
When a job scores above the threshold, calls the configured LLM to
rewrite the resume, then saves the result as a PDF using fpdf2.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

from fpdf import FPDF

from modules.llm import call_llm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCORE_THRESHOLD = 50  # minimum match_score to trigger tailoring
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "resumes")

# ---------------------------------------------------------------------------
# LLM prompt for resume rewriting
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert resume writer specialising in Data Science and Machine Learning.

You will receive:
1. A **Job Description** the candidate wants to apply for.
2. A **Base Resume** of the candidate.

The candidate has 3 years of professional experience and is transitioning from
a software testing / QA background into Data Science / ML.

**Rewrite** the resume to align perfectly with the job description.
Produce **ONLY** a valid JSON object with these keys:

{
  "summary": "<3-4 sentence professional summary heavily emphasising
    data-centric skills, Python proficiency, and relevant project work>",
  "skills": ["<list of top skills to highlight>"],
  "experience_bullets": [
    "<bullet 1 — reframed to emphasise data/ML work>",
    "<bullet 2>",
    "..."
  ],
  "education_and_certs": "<education + certifications, one paragraph>"
}

Rules:
- Heavily emphasise Python, data analysis, ML, and any relevant projects.
- Reframe testing experience as data-quality, automation, pipeline, or
  analytical work wherever truthful.
- Do NOT fabricate experience — only reframe and highlight.
- Return ONLY valid JSON, no markdown fences.
"""


def _build_prompt(job_description: str, base_resume: str) -> str:
    return (
        f"### Job Description\n{job_description}\n\n"
        f"### Base Resume\n{base_resume}"
    )


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------


class _ResumePDF(FPDF):
    """Minimal clean PDF layout for a tailored resume."""

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "Tailored Resume", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(4)

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 8, f"  {title}", new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(2)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def bullet_list(self, items: list[str]):
        self.set_font("Helvetica", "", 10)
        for item in items:
            self.cell(6)
            self.multi_cell(0, 6, f"•  {item}")
            self.ln(1)
        self.ln(2)


def _generate_pdf(content: dict, company: str, job_title: str) -> str:
    """Build a PDF from the LLM-generated resume content and save it."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Sanitise filename components
    safe_company = re.sub(r"[^a-zA-Z0-9]+", "_", company)[:30]
    safe_title = re.sub(r"[^a-zA-Z0-9]+", "_", job_title)[:30]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_company}_{safe_title}_{timestamp}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    pdf = _ResumePDF()
    pdf.add_page()

    # Summary
    pdf.section_title("Professional Summary")
    pdf.body_text(content.get("summary", ""))

    # Skills
    pdf.section_title("Key Skills")
    skills = content.get("skills", [])
    if skills:
        pdf.body_text(", ".join(skills))

    # Experience
    pdf.section_title("Professional Experience")
    bullets = content.get("experience_bullets", [])
    if bullets:
        pdf.bullet_list(bullets)

    # Education
    pdf.section_title("Education & Certifications")
    pdf.body_text(content.get("education_and_certs", ""))

    pdf.output(filepath)
    return os.path.abspath(filepath)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tailor_resume(
    job_description: str,
    base_resume: str,
    company: str,
    job_title: str,
    match_score: int,
    threshold: int = SCORE_THRESHOLD,
    provider: str = "gemini",
) -> str | None:
    """
    If the match_score meets the threshold, call the LLM to rewrite the
    resume and save it as a PDF.

    Parameters
    ----------
    provider : str
        ``"gemini"`` or ``"groq"``.

    Returns
    -------
    str or None
        Absolute path to the generated PDF, or ``None`` if the score
        was below the threshold.
    """
    if match_score < threshold:
        return None

    try:
        raw = call_llm(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=_build_prompt(job_description, base_resume),
            provider=provider,
        )
    except Exception as exc:
        print(f"  ⚠️  Resume tailoring API call failed: {exc}")
        return None

    # Parse JSON (strip possible markdown fences)
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        content = json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"  ⚠️  Could not parse tailored resume JSON:\n{raw[:200]}")
        return None

    return _generate_pdf(content, company, job_title)
