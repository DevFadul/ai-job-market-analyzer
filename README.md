# AI Job Market Analyzer

Turns a CSV of AI job postings into numbers you can trust and reports you can actually show someone. No dashboard required.

## What it does

- Loads `data/ai_job_dataset.csv`
- Cleans dates and coerces numeric fields where the analysis needs them
- Computes salary patterns by experience, industry, and company size
- Pulls **top skills** from comma-separated `required_skills`
- Looks at education mix, benefits vs pay, and remote ratio vs pay
- Prints a **structured text report** to the terminal
- Optionally writes a **PDF** and a short **Markdown** executive summary under `reports/`

## Requirements

- Python 3.11+ (3.13 works with the pinned stack in this repo)
- Dependencies: see `requirements.txt` (`pandas`, `numpy`, `matplotlib`, `reportlab`, `pillow`, etc.)

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
## Run
From the project root (folder that contains data/ and main/):
```bash
python main/main.py
```
The script resolves the data path from main/main.py’s location, so you don’t have to cd into main/ unless you prefer to.

### If PDF generation fails with No module named 'reportlab', install the reporting stack:

```bash
pip install reportlab matplotlib pillow
```
The script will still print the text report if PDF deps are missing; it only skips the PDF/Markdown step and tells you what to install.

## Outputs

| Output| Path |
| -------- | -------- |
| Console | (full board-style text report) |
| PDF | reports/ai_job_market_board_report.pdf |
| Markdown | reports/ai_job_market_executive_report.md |

Regenerate anytime by running main/main.py again.

## Project layout

### input
data/ai_job_dataset.csv    
### load, clean, analyze, text report, orchestration
main/main.py               
main/pdf_report.py         
### charts + PDF + Markdown summary
reports/                  
### generated artifacts (gitignore if you don’t want them in version control)
requirements.txt

## How the analysis is built
analyze_salary — Mean/median salary by experience_level (EN → EX), mean salary by industry (ranked), mean/median by company_size (S, M, L).

analyze_skills — Top skills by frequency (split on commas in required_skills), education counts, Pearson correlation between benefits_score and salary_usd, and mean salary by benefits tertile when bucketing works.

analyze_remote — Mean/median salary by remote_ratio (0 / 50 / 100) and correlation with salary.

The PDF layers a longer narrative (cover, key findings, implications, numbered insight sections, charts) on top of the same underlying numbers—not a second dataset.

## Honest limitations
Correlations are associations, not proof of cause.
Industry and remote numbers don’t control for seniority mix, location, or job title—so treat rankings as signals, not final truth.
benefits_score is a coarse scalar; weak correlation doesn’t mean “benefits don’t matter,” only that this score doesn’t track pay linearly here.
