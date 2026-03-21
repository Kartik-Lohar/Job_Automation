# Task Tracking

This document tracks the ongoing and upcoming tasks for the Stealth Job Pipeline project.

## Completed Tasks [x]
- [x] Refactor overall project structure into `modules/`, `data/`, `templates/`.
- [x] Implement CLI interface in `main.py` with arguments for title, location, threshold.
- [x] LinkedIn Scraper with `undetected_chromedriver`.
- [x] Naukri Scraper mirroring LinkedIn's stealth approach.
- [x] LLM evaluation module (Gemini, Groq) to score job matches.
- [x] Resume tailorer using HTML/Jinja2 and Chrome backend for PDF generation.
- [x] Fix Windows `undetected_chromedriver` process management bugs (`NoSuchWindowException` / `WinError 6`).
- [x] Create project sync files (`AI_Sync.md`, `task.md`, `implementation_plan.md`) for cross-machine AI collaboration.

## Current & In-Progress Tasks [/]
- [/] Ensure stability of the headless PDF extraction under load.
- [/] Test the full pipeline on a fresh machine environment to confirm `requirements.txt` is complete.
- [/] Implement CSS/Content constraints to strictly ensure the tailored PDF resume fits on a single page.
- [/] Fix profile links in the generated PDF so that they remain genuinely clickable.

## Upcoming Tasks [ ]
- [ ] Add support for additional job boards (e.g., Indeed, Glassdoor).
- [ ] Implement an automated email-sending or auto-apply mechanism using the generated tailored resumes.
- [ ] Add a lightweight web UI or dashboard to view the generated `job_applications.xlsx` and PDF links directly in the browser visually instead of using Excel.
- [ ] Improve the resume tailoring prompt to handle extremely technical edge-cases in the Job Description.
