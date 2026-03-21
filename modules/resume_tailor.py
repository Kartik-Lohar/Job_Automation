"""
Resume Tailoring Module
=======================
When a job scores above the threshold, calls the configured LLM to
rewrite the resume, then saves the result as a PDF using fpdf2.
"""

from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from modules.browser import create_stealth_driver, force_quit_driver
from modules.llm import call_llm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCORE_THRESHOLD = 50  # minimum match_score to trigger tailoring
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "resumes")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# ---------------------------------------------------------------------------
# LLM prompt for resume rewriting
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert resume writer specialising in Data Science and Machine Learning.

You will receive:
1. A **Job Description** the candidate wants to apply for.
2. A **Base Resume** of the candidate.

**Rewrite** the resume to align perfectly with the job description while maintaining the candidate's core identity. 
Produce **ONLY** a valid JSON object with exactly these keys:

{
  "name": "Candidate Name",
  "phone": "Phone Number",
  "email": "Email Address",
  "location": "City, Country",
  "linkedin": "LinkedIn URL",
  "portfolio": "Portfolio/Website URL",
  "github": "GitHub URL",
  "professional_summary": "A 3-4 sentence summary tailored to the JD.",
  "domains": ["Domain 1", "Domain 2"],
  "key_skills": {
    "Programming": "Python, SQL, etc.",
    "ML Frameworks": "PyTorch, Scikit-learn, etc.",
    "Tools": "Git, Docker, etc."
  },
  "experience": [
    {
      "company": "Company Name",
      "location": "Location",
      "title": "Job Title",
      "dates": "Start - End",
      "bullets": ["Bullet 1", "Bullet 2"],
      "skills_used": "List of skills used in this role"
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "dates": "Date/Duration",
      "tech_stack": "Tech 1, Tech 2",
      "primary_goal": "What was the goal?",
      "solution": "How did you solve it?",
      "result": "What was the outcome?"
    }
  ],
  "certifications": [
    {
      "name": "Cert Name",
      "issuer": "Issuer",
      "date": "Month Year"
    }
  ],
  "education": {
    "college": "University Name",
    "location": "City, State",
    "degree": "Degree Name",
    "score": "GPA/Percentage",
    "dates": "Start - End"
  }
}

Rules:
- Reframe all bullets and summaries to emphasize Data Science/ML skills mentioned in the JD.
- Keep contact info truthful from the base resume.
- Return ONLY valid JSON, no markdown fences.
"""


def _build_prompt(job_description: str, base_resume: str) -> str:
    return (
        f"### Job Description\n{job_description}\n\n"
        f"### Base Resume\n{base_resume}"
    )


# ---------------------------------------------------------------------------
def _generate_pdf(content: dict, company: str, job_title: str, driver: any = None) -> str:
    """
    Build a PDF by rendering the Jinja2 HTML template and using
    Chrome headless to print it to a pixel-perfect PDF.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMPLATE_DIR, exist_ok=True)

    # 1. Setup Jinja2 and render HTML
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    try:
        template = env.get_template("resume.html")
    except Exception as exc:
        raise FileNotFoundError(f"Missing templates/resume.html: {exc}")

    rendered_html = template.render(**content)

    # Save to a temporary HTML file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_company = re.sub(r"[^a-zA-Z0-9]+", "_", company)[:30]
    safe_title = re.sub(r"[^a-zA-Z0-9]+", "_", job_title)[:30]
    
    filename_base = f"{safe_company}_{safe_title}_{timestamp}"
    temp_html_path = os.path.join(OUTPUT_DIR, f"{filename_base}.html")
    pdf_path = os.path.join(OUTPUT_DIR, f"{filename_base}.pdf")

    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    # 2. Print to PDF via Chrome Headless
    local_driver = False
    if driver is None:
        driver = create_stealth_driver(headless=True, use_subprocess=True)
        local_driver = True
    
    try:
        # Load local HTML file
        driver.get(f"file:///{os.path.abspath(temp_html_path)}")
        
        # Give it a tiny moment to render
        import time
        time.sleep(1)

        # Use Chrome DevTools Protocol to generate PDF
        print_options = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
            "marginTop": 0, "marginBottom": 0, "marginLeft": 0, "marginRight": 0
        }
        
        result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
        
        # Decode and save the PDF
        with open(pdf_path, "wb") as f:
            f.write(base64.b64decode(result['data']))
            
    finally:
        if local_driver and driver:
            force_quit_driver(driver)
            
        # Optional: clean up the temp HTML file
        if os.path.exists(temp_html_path):
            try:
                os.remove(temp_html_path)
            except Exception:
                pass

    return os.path.abspath(pdf_path)


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
    driver: any = None,
) -> str | None:
    """
    If the match_score meets the threshold, call the LLM to rewrite the
    resume and save it as a PDF.

    Parameters
    ----------
    provider : str
        ``"gemini"`` or ``"groq"``.
    driver : uc.Chrome, optional
        An existing driver instance to reuse for printing.

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

    return _generate_pdf(content, company, job_title, driver=driver)
