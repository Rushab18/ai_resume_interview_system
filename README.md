# AI-Powered Resume-Based Interview System

This is a Flask-based web application that simplifies and automates the preliminary stages of recruitment. It uses Cohere's LLM to:

* Extract text from uploaded resumes (PDFs)
* Generate customized interview questions
* Evaluate user responses
* Assign ATS scores based on resume quality

It includes user authentication, admin dashboards, and PDF reporting.

---

## Project Structure and Purpose

### 1. `app.py` (Main Application)

Handles all Flask routes:

* `/login`, `/register`: User authentication
* `/upload_resume`: Upload and parse PDF resumes
* `/evaluate_answer`: Evaluate AI-generated answers
* `/check_ats`: Calculate ATS score
* `/admin_dashboard`: Admin dashboard view
* `/download_pdf`: Export admin report

### 2. `templates/` (HTML Templates)

Contains:

* `login.html`
* `register.html`
* `index.html`
* `questions.html`
* `admin_dashboard.html`

These handle front-end rendering for each route.

### 3. `static/`

Include static assets like CSS/JS (optional).

---

## Requirements

Install required Python libraries:

```bash
pip install flask cohere PyPDF2 reportlab werkzeug python-dotenv
```

---

## API Key Setup (Cohere)

This app depends on the Cohere API. **Do not hardcode the API key.**

### Option 1: Using Environment Variable

```bash
export COHERE_API_KEY=your_api_key
```

### Option 2: Using `.env` file

Install `python-dotenv`:

```bash
pip install python-dotenv
```

Create a `.env` file in the root:

```
COHERE_API_KEY=your_api_key
```

In `app.py`, load it using:

```python
from dotenv import load_dotenv
load_dotenv()
co = cohere.Client(os.getenv("COHERE_API_KEY"))
```

---

## Running the App

```bash
python app.py
```

Then visit: `http://localhost:5000`

---

## Admin Credentials

```
Username: admin
Password: admin123
```

Use these to access the admin dashboard and download reports.

---

## Security Features

* Passwords are hashed using Werkzeug
* Sessions are managed using Flask's secure session cookie

---

## Report Generation

The `/download_pdf` route allows the admin to generate a detailed PDF report of all interview and ATS evaluations using ReportLab.

---

## License

Licensed under Creative Commons BY-NC-SA 4.0:

> Non-commercial use allowed with attribution and same license.

---

## Contact & Credits

Developed by **Rushab Upadhya**

* Email: [your.email@example.com](mailto:rushab181@gmail.com)
* LinkedIn: [https://linkedin.com/in/your-profile](https://linkedin.com/in/rushab-upadhya)

**Special thanks to:**

* Cohere.ai
* Flask
* ReportLab
* PyPDF2
