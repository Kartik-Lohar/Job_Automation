"""
AI Evaluation & Scoring Module
===============================
Passes a scraped Job Description and base resume to the configured LLM,
returning a structured JSON assessment with match_score, missing_skills,
and readiness_assessment tailored for a 3-year professional transitioning
from a testing background into Data Science / ML.
"""

import json
import re

from modules.llm import call_llm

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert career-matching assistant specialising in Data Science
and Machine Learning roles.  You will receive two inputs:
1. A **Job Description**.
2. A **Base Resume**.

The candidate has **3 years of professional experience** and is
**transitioning from a software testing / QA background** into Data Science
and Machine Learning.

Analyse how well the resume matches the job and return **ONLY** a valid JSON
object (no markdown fences, no commentary) with exactly these keys:

{
  "match_score": <integer 1-100>,
  "missing_skills": [<list of skill strings the candidate lacks for THIS role>],
  "readiness_assessment": "<A brief 2-3 sentence note on how well a candidate
    with 3 years of professional experience, transitioning from a testing
    background, fits this specific role. Mention concrete strengths and gaps.>"
}

Rules:
- match_score must be an integer between 1 and 100.
- missing_skills must be a JSON array of strings (may be empty).
- readiness_assessment must be a single string, not a list.
- Do NOT include any text outside the JSON object.
"""


def _build_user_prompt(job_description: str, base_resume: str) -> str:
    return (
        f"### Job Description\n{job_description}\n\n"
        f"### Base Resume\n{base_resume}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_job(
    job_description: str,
    base_resume: str,
    provider: str = "gemini",
) -> dict:
    """
    Send a job description + resume to the LLM and return a parsed dict.

    Parameters
    ----------
    provider : str
        ``"gemini"`` or ``"groq"``.

    Returns
    -------
    dict
        {
            "match_score": int,
            "missing_skills": list[str],
            "readiness_assessment": str
        }
    """
    raw_text = call_llm(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(job_description, base_resume),
        provider=provider,
    )

    parsed = _parse_json(raw_text)
    _validate(parsed)
    return parsed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_json(raw: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse LLM response as JSON.\nRaw:\n{raw}"
        ) from exc


def _validate(data: dict) -> None:
    required = {"match_score", "missing_skills", "readiness_assessment"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"Missing keys: {missing}\nReceived: {data}")

    if not isinstance(data["match_score"], (int, float)):
        raise ValueError(f"match_score must be a number, got {type(data['match_score'])}")
    if not isinstance(data["missing_skills"], list):
        raise ValueError(f"missing_skills must be a list, got {type(data['missing_skills'])}")
    if not isinstance(data["readiness_assessment"], str):
        raise ValueError(f"readiness_assessment must be str, got {type(data['readiness_assessment'])}")

    data["match_score"] = max(1, min(100, int(data["match_score"])))


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sample_jd = (
        "We are hiring a Data Scientist with 2-4 years of experience. "
        "Must know Python, pandas, scikit-learn, SQL, and have experience "
        "with ML model deployment. Nice to have: deep learning, NLP, MLOps."
    )
    sample_resume = (
        "QA Engineer with 3 years of experience in automated testing using "
        "Python, Selenium, and Jenkins. Skilled in SQL, data analysis with "
        "pandas, and basic ML projects using scikit-learn. Completed "
        "certifications in Data Science and Machine Learning."
    )

    print("=" * 60)
    print("Evaluation Module — Smoke Test")
    print("=" * 60)

    result = evaluate_job(sample_jd, sample_resume, provider="groq")

    print(f"\nMatch Score        : {result['match_score']}")
    print(f"Missing Skills     : {result['missing_skills']}")
    print(f"Readiness          : {result['readiness_assessment']}")
    print("\n✅ Done.")
