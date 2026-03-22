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
- **Stealth Scraping**: Uses `undetected-chromedriver` to bypass bot protection on LinkedIn and Naukri.
- **Config-Driven**: Control all job titles, locations, and system paths from a single `config.yaml`.
- **Combinatorial Search**: Search for multiple titles and locations at once.
- **Freshness Control**: Toggle between "Past 24 Hours" or "All Time" job listings.
- **AI-Powered Evaluation**: Automatically scores job descriptions against your resume using Gemini or Groq.
- **One-Page Resume Tailoring**: Dynamically generates a custom LaTeX-style HTML/PDF resume for high-scoring jobs.
- **Auto-Cleanup**: Automatically keeps your output directory clean from failed or interrupted runs.

## 🛠️ Usage
1.  **Configure**: Edit `config.yaml` with your details and target job titles.
2.  **Run**: Execute the pipeline with one command:
    ```bash
    py main.py
    ```
3.  **Review**: Check the `output/run_timestamp/` folder for your Excel summary and tailored PDF resumes.

---

## ⚙️ Setup & Installation

**1. Clone the repository**
```bash
git clone https://github.com/Kartik-Lohar/Job_Automation.git
cd Job_Automation
```

**2. Install Dependencies**
```bash
pip install -r requirements.txt
```

**3. Configure Environment Variables**
Create a `.env` file in the root directory and add your preferred LLM API keys:
```env
GEMINI_API_KEY=your_google_gemini_key_here
GROQ_API_KEY=your_groq_api_key_here
```

**4. Add Your Base Resume**
Drop your base resume into the project root. It can be named `resume.pdf` or `resume.txt`.

---

## 💻 Usage

Run the complete pipeline (Scrape -> Evaluate -> Tailor) with a single command:

```bash
python main.py \
  --platform linkedin \
  --title "Data Scientist" \
  --location "Bangalore" \
  --max-jobs 10 \
  --resume resume.pdf \
  --threshold 60 \
  --llm gemini \
  --headless
```

### CLI Arguments:
- `--platform`: Target job board (`linkedin` or `naukri`). Default is `linkedin`.
- `--title`: The job title you're searching for. Default is `Data Scientist`.
- `--location`: Target city or region. Default is `Bangalore`.
- `--max-jobs`: How many jobs to scrape before stopping. Default is `25`.
- `--resume`: Explicit path to your base `.pdf` or `.txt` resume. (Defaults to `resume.pdf` in root).
- `--threshold`: Only generate a tailored PDF if the AI match score is `>=` this number (0-100). Default is `50`.
- `--llm`: Choose the AI LLM provider (`gemini` or `groq`). Default is `gemini`.
- `--headless` / `--no-headless`: Run the scraping browser in the background. (Note: Resume PDF generation always happens in headless).

---

## 🏗️ Architecture Design
1. **Phase 1 (Scraper)**: `modules/scrapers/` scrapes the data and passes it to `modules/data_manager.py` to be saved in an Excel sheet.
2. **Phase 2 (Evaluation)**: `modules/evaluation.py` loops through the jobs. It sends the JD and your resume to the LLM.
3. **Phase 3 (Tailoring)**: If the job passes the threshold score, `modules/resume_tailor.py` dynamically injects keywords and achievements into `templates/resume.html` via Jinja2. It then uses Chrome DevTools (CDP) to print a customized PDF directly into the `output/` directory so you can apply immediately!

---

## 📌 Known Issues & Upcoming Features
- **Strict Single Page Constraint**: We are actively refining CSS variables to ensure the generated tailored resumes never accidentally bleed onto a second page. (Currently in progress).
- **Clickable Profile Links**: Ongoing patch to ensure custom profile links inside the output PDFs remain clickable.

*Happy Job Hunting! automating the boring stuff so you can focus on the interviews.*
