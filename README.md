<div align="center">
  <h1>🚀 Stealth Job Application Pipeline</h1>
  <p><strong>A fully automated, AI-powered job application tool that scrapes, evaluates, and dynamically tailors resumes.</strong></p>

  <p>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python 3.9+"></a>
    <a href="https://github.com/ultrafunkamsterdam/undetected-chromedriver"><img src="https://img.shields.io/badge/Browser-Undetected_Chromedriver-red" alt="Undetected Chromedriver"></a>
    <a href="https://ai.google.dev/"><img src="https://img.shields.io/badge/AI-Gemini%20%7C%20Groq-orange" alt="LLMs"></a>
  </p>
</div>

---

## 🚀 Features
- **🕵️ Stealth Scraping**: Uses `undetected_chromedriver` to bypass bot protection on LinkedIn and Naukri.
- **⚙️ Config-Driven Orchestration**: Control all job titles, locations, and system paths from a single `config.yaml`. No more complex CLI flags!
- **🔄 Combinatorial Search**: Search for multiple titles (e.g., ML Engineer, Data Scientist) across multiple locations (e.g., Remote, Gurgaon) in one go.
- **🕒 Freshness Control**: Toggle a 24-hour filter to only see the most recent postings.
- **🧠 AI Match Scoring**: Uses Gemini or Groq to critically evaluate matching scores.
- **📄 Dynamic Resume Tailoring**: Generates a custom LaTeX-style HTML/PDF resume for high-scoring jobs.
- **📊 Automated Logging**: Saves results to Excel and links to tailored PDFs in timestamped folders.
- **✨ Auto-Cleanup**: Automatically deletes empty run folders if a session is interrupted or fails.

---

## 🏗️ System Architecture
The pipeline is designed as a modular, configuration-driven engine:

1.  **Config Loader**: `main.py` parses `config.yaml` to handle multi-keyword and multi-location arrays.
2.  **Scraper Engine**: `modules/scrapers/` uses platform-specific logic. 
    - *Naukri Fix*: Features custom slug-generation to bypass React-router redirects that used to strip query parameters.
    - *Conflict Resolver*: Automatically prioritizes "Remote" searches if mixed with physical cities to ensure maximum job yield.
3.  **Evaluation Phase**: `modules/evaluation.py` passes data to LLMs (Gemini/Groq).
4.  **Tailoring Phase**: `modules/resume_tailor.py` uses Jinja2 and Chrome Headless to generate one-page PDFs. It deterministically injects profile links from your config to prevent AI hallucination.
5.  **Output Management**: Results are stored in `output/run_YYYYMMDD_HHMMSS/` for perfect session isolation.

---

## 🛠️ Setup & Usage

### 1. Configure
Edit `config.yaml` in the root:
```yaml
search:
  titles:
    - "Machine Learning Engineer"
    - "Data Scientist"
  locations:
    - "Remote"
    - "Gurgaon"
  past_24_hours: true
```

### 2. Environment
Add your API keys to `.env`:
```env
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
```

### 3. Run
```bash
python main.py
```

---

## 📌 Current Status & Known Issues
- **✅ Fixed**: Naukri multi-title search redirects and query parameter stripping.
- **✅ Fixed**: Remote vs City search collisions (Remote now overrides and prioritizes correctly).
- **✅ Fixed**: LLM numeric anchoring (Scores are now critically calculated).
- **📝 Ongoing**: Refining CSS for perfect 1-page PDF rendering across varying JD lengths.

*Happy Job Hunting! automating the boring stuff so you can focus on the interviews.*
