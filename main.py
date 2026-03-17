"""
Stealth Job Pipeline — Entry Point
====================================
Single command runs the full pipeline automatically:

  python main.py --platform linkedin --title "Data Scientist" --location "Bangalore" --max-jobs 5 --no-headless --resume resume.pdf

Flow:  Scrape → Save to Excel → Close browser → Gemini evaluation → Tailored PDFs → Update Excel
"""

from __future__ import annotations

import argparse
import os

# ---------------------------------------------------------------------------
# Hardcoded resume path — place your resume PDF here
# ---------------------------------------------------------------------------

DEFAULT_RESUME_PATH = os.path.join(os.path.dirname(__file__), "resume.pdf")

DEFAULT_EXCEL = os.path.join(
    os.path.dirname(__file__), "data", "job_applications.xlsx"
)

# ---------------------------------------------------------------------------
# Resume loader (supports .pdf and .txt)
# ---------------------------------------------------------------------------


def _load_resume(filepath: str) -> str:
    """
    Load resume text from a file.
    Supports .pdf (extracts text via PyPDF2) and .txt (plain read).
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise ValueError(f"Could not extract any text from PDF: {filepath}")
        return text

    else:
        # .txt or any other text file
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()


# ═══════════════════════════════════════════════════════════════════════════
# PHASE A — SCRAPE
# ═══════════════════════════════════════════════════════════════════════════


def phase_scrape(
    platform: str,
    title: str,
    location: str,
    max_jobs: int,
    headless: bool,
    excel_path: str,
) -> str | None:
    """Scrape jobs and save raw data to Excel. Returns saved filepath or None."""
    from modules.scraper import scrape_jobs
    from modules.data_manager import save_jobs_to_excel

    print(f"\n{'═' * 60}")
    print(f"  PHASE 1 — SCRAPING")
    print(f"{'═' * 60}")
    print(f"  Platform : {platform}")
    print(f"  Title    : {title}")
    print(f"  Location : {location}")
    print(f"  Max jobs : {max_jobs}")
    print(f"  Headless : {headless}\n")

    jobs, driver = scrape_jobs(
        platform=platform,
        job_title=title,
        location=location,
        max_jobs=max_jobs,
        headless=headless,
    )

    # Close browser immediately
    if driver:
        try:
            driver.quit()
        except OSError:
            pass
        # Prevent __del__ from trying to quit again during garbage collection
        driver.__del__ = lambda: None
        print("\n🛑  Browser closed.")

    if not jobs:
        print("\n⚠️   No jobs found. Try different search terms or --no-headless.")
        return None

    path = save_jobs_to_excel(jobs, filepath=excel_path)
    print(f"\n📊  {len(jobs)} job(s) saved to: {path}")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# PHASE B — EVALUATE
# ═══════════════════════════════════════════════════════════════════════════


def phase_evaluate(
    excel_path: str,
    resume_text: str,
    threshold: int,
    llm_provider: str = "gemini",
) -> None:
    """Read Excel, evaluate each job via LLM, generate PDFs, update Excel."""
    from modules.data_manager import load_jobs_from_excel, update_excel
    from modules.evaluation import evaluate_job
    from modules.resume_tailor import tailor_resume

    print(f"\n{'═' * 60}")
    print(f"  PHASE 2 — AI EVALUATION & RESUME TAILORING")
    print(f"{'═' * 60}")
    print(f"  Excel     : {excel_path}")
    print(f"  LLM       : {llm_provider}")
    print(f"  Threshold : {threshold}\n")

    df = load_jobs_from_excel(excel_path)

    if df.empty:
        print("⚠️   Excel is empty — nothing to evaluate.")
        return

    total = len(df)
    scored = 0
    pdfs = 0

    for idx in range(total):
        row = df.iloc[idx]
        title = row.get("Job Title", "N/A")
        company = row.get("Company", "N/A")
        jd = str(row.get("Job Description", ""))

        print(f"── [{idx + 1}/{total}] {title} @ {company}")

        if not jd or jd == "nan" or len(jd.strip()) < 20:
            print("   ⚠️  Skipping — no job description available.")
            continue

        # --- LLM evaluation ----------------------------------------------
        try:
            result = evaluate_job(jd, resume_text, provider=llm_provider)
            score = result["match_score"]
            missing = result["missing_skills"]
            readiness = result["readiness_assessment"]

            df.at[idx, "Match Score"] = score
            df.at[idx, "Missing Skills"] = ", ".join(missing) if missing else ""
            df.at[idx, "Readiness Assessment"] = readiness
            scored += 1

            print(f"   ✅ Score: {score}  |  Missing: {missing}")
            print(f"   📝 {readiness[:120]}…" if len(readiness) > 120 else f"   📝 {readiness}")

        except Exception as exc:
            print(f"   ❌ Evaluation failed: {exc}")
            df.at[idx, "Match Score"] = 0
            df.at[idx, "Missing Skills"] = ""
            df.at[idx, "Readiness Assessment"] = f"ERROR: {exc}"
            continue

        # --- Resume tailoring (score ≥ threshold) ------------------------
        if score >= threshold:
            print(f"   📝 Score ≥ {threshold} — generating tailored resume PDF…")
            try:
                pdf_path = tailor_resume(
                    job_description=jd,
                    base_resume=resume_text,
                    company=str(company),
                    job_title=str(title),
                    match_score=score,
                    threshold=threshold,
                    provider=llm_provider,
                )
                if pdf_path:
                    df.at[idx, "Resume PDF Path"] = pdf_path
                    pdfs += 1
                    print(f"   📄 Saved: {pdf_path}")
            except Exception as exc:
                print(f"   ⚠️  Resume tailoring failed: {exc}")

    # --- Save updated Excel -----------------------------------------------
    saved = update_excel(df, excel_path)
    print(f"\n{'═' * 60}")
    print(f"  ✅  PIPELINE COMPLETE")
    print(f"{'═' * 60}")
    print(f"  Jobs evaluated  : {scored}/{total}")
    print(f"  Resumes created : {pdfs}")
    print(f"  Excel updated   : {saved}")
    print(f"{'═' * 60}\n")


# ═══════════════════════════════════════════════════════════════════════════
# CLI — single command, both phases run automatically
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stealth Job Pipeline — scrape & evaluate in one go",
    )
    parser.add_argument("--platform", choices=["linkedin", "naukri"],
                        default="linkedin", help="Job platform (default: linkedin)")
    parser.add_argument("--title", default="Data Scientist",
                        help='Job title (default: "Data Scientist")')
    parser.add_argument("--location", default="Bangalore",
                        help='Location (default: "Bangalore")')
    parser.add_argument("--max-jobs", type=int, default=25,
                        help="Max jobs to scrape (default: 25)")
    parser.add_argument("--excel", default=DEFAULT_EXCEL,
                        help="Excel file path")
    parser.add_argument("--resume", default=None,
                        help="Path to a .txt resume file (uses default if omitted)")
    parser.add_argument("--threshold", type=int, default=50,
                        help="Min score to generate tailored resume (default: 50)")
    parser.add_argument("--llm", choices=["gemini", "groq"],
                        default="gemini",
                        help="LLM provider: gemini (default) or groq")

    headless_grp = parser.add_mutually_exclusive_group()
    headless_grp.add_argument("--headless", action="store_true", default=True)
    headless_grp.add_argument("--no-headless", action="store_false",
                              dest="headless")

    args = parser.parse_args()

    # --- Load resume (hardcoded path or --resume override) -----------------
    resume_path = args.resume if args.resume else DEFAULT_RESUME_PATH

    if not os.path.isfile(resume_path):
        print(f"❌  Resume file not found: {resume_path}")
        print("    Place your resume.pdf in the project root, or use --resume <path>")
        return

    resume_text = _load_resume(resume_path)
    print(f"📄  Resume loaded from: {resume_path}")
    print(f"    ({len(resume_text)} characters extracted)")

    # --- Phase 1: Scrape -------------------------------------------------
    saved_excel = phase_scrape(
        platform=args.platform,
        title=args.title,
        location=args.location,
        max_jobs=args.max_jobs,
        headless=args.headless,
        excel_path=args.excel,
    )

    if not saved_excel:
        return

    # --- Phase 2: Evaluate (auto-triggered, uses the ACTUAL saved path) ---
    phase_evaluate(
        excel_path=saved_excel,
        resume_text=resume_text,
        threshold=args.threshold,
        llm_provider=args.llm,
    )


if __name__ == "__main__":
    main()
