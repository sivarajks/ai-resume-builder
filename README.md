# AI Resume Builder (ATS-friendly)

This is a Flask app that uses OpenAI (ChatGPT) to generate ATS-friendly resumes and exports them on-the-fly as:
- PDF (ReportLab)
- Word (.docx) (python-docx)

## Quick start (local)

1. Clone the repo
2. Create virtualenv: `python -m venv venv && source venv/bin/activate`
3. Install: `pip install -r requirements.txt`
4. Set environment variables:
   - `OPENAI_API_KEY` (required)
   - `FLASK_SECRET` (optional)
5. Run: `python app.py` or `flask run`

## Deploy

- Works on Render / Railway / Heroku.
- Add `OPENAI_API_KEY` and `FLASK_SECRET` in your host's environment settings.
- Use the Procfile included for Heroku/Render.

