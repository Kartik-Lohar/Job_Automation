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

## 🔥 Features
- **🕵️ Stealth Scraping**: Uses `undetected_chromedriver` to safely scrape LinkedIn and Naukri without triggering anti-bot protections.
- **🧠 AI Evaluation**: Uses Google Gemini or Groq to compare the scraped Job Description against your base resume to generate a Match Score, Missing Skills, and Readiness Assessment.
- **📄 Dynamic PDF Resumes**: For jobs scoring above a specific threshold, it injects the AI-tailored content into a beautiful HTML/Jinja2 template, rendering a crisp, tailored PDF resume using headless Chrome.
- **📊 Excel Tracking**: Automatically logs every scraped job, AI evaluation feedback, and local paths to the tailored resumes into a clean `data/job_applications.xlsx` log.

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
