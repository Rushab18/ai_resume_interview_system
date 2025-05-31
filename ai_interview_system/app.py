from flask import Flask, render_template, request, redirect, session, jsonify, send_file
import cohere
import PyPDF2
import os
import re
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io

app = Flask(__name__)
app.secret_key = 'your_secret_key'

co = cohere.Client('')

USER_CREDENTIALS = {
    'admin': {
        'password': generate_password_hash('admin123'),
        'role': 'admin'
    }
}

SESSION_DATA = []

@app.route('/')
def index():
    if 'user' not in session:
        return redirect('/login')
    return render_template('index.html')

@app.before_request
def require_login():
    allowed_routes = ['login', 'register', 'static']
    if request.endpoint not in allowed_routes and 'user' not in session:
        return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = USER_CREDENTIALS.get(username)
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            session['role'] = user['role']
            if user['role'] == 'admin':
                return redirect('/admin_dashboard')
            return redirect('/')
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USER_CREDENTIALS:
            return render_template('register.html', error="Username already exists")
        hashed_password = generate_password_hash(password)
        USER_CREDENTIALS[username] = {'password': hashed_password, 'role': 'user'}
        return redirect('/login')
    return render_template('register.html')

@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    if session.get('role') != 'user':
        return redirect('/')
    if 'resume' not in request.files:
        return "No file part"
    file = request.files['resume']
    if file.filename == '':
        return "No selected file"
    if file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ''
        for page in pdf_reader.pages:
            text += page.extract_text()

        session['resume_text'] = text
        session['resume_filename'] = file.filename

        prompt = f"Generate 5 interview questions based on the following resume:\n{text}\nQuestions:"
        response = co.generate(
            model="command",
            prompt=prompt,
            max_tokens=200,
            temperature=0.7
        )
        questions = response.generations[0].text.strip().split('\n')
        questions = [q for q in questions if q.strip()]
        session['questions'] = questions
        return render_template('questions.html', questions=enumerate(questions, 1))
    return "File upload failed"

@app.route('/evaluate_answer', methods=['POST'])
def evaluate_answer():
    data = request.get_json()
    answer = data['answer']

    eval_prompt = f"Evaluate the following interview answer. Return only the score out of 10 in the first line (e.g. 8/10) and give 1-2 lines of feedback below.\nAnswer:\n{answer}\nScore:"
    response = co.generate(
        model="command",
        prompt=eval_prompt,
        max_tokens=100,
        temperature=0.7
    )

    output = response.generations[0].text.strip()
    lines = output.strip().splitlines()
    score = None
    feedback = ""

    for i, line in enumerate(lines):
        match = re.search(r'(\d+)/10', line)
        if match:
            score = int(match.group(1))
            feedback_lines = lines[i+1:] if i + 1 < len(lines) else []
            feedback = ' '.join(feedback_lines).strip()
            break

    if score is None or not feedback:
        return jsonify({'error': 'AI did not return a valid score or feedback.', 'raw': output}), 500

    found = False
    for record in SESSION_DATA:
        if record['user'] == session['user']:
            record['interview_score'] = record.get('interview_score', 0) + score
            found = True
            break

    if not found:
        SESSION_DATA.append({
            'user': session['user'],
            'resume_filename': session.get('resume_filename', 'N/A'),
            'interview_score': score,
            'ats_score': None,
            'ats_feedback': ''
        })

    return jsonify({'evaluation': f"{score}/10 - {feedback}"})

@app.route('/check_ats', methods=['POST'])
def check_ats():
    file = request.files.get('resume')
    if not file:
        return jsonify({'score': 0, 'feedback': 'No file uploaded'}), 400

    pdf_reader = PyPDF2.PdfReader(file)
    text = ''
    for page in pdf_reader.pages:
        text += page.extract_text()

    session['resume_text'] = text
    session['resume_filename'] = file.filename

    for record in SESSION_DATA:
        if record['user'] == session['user']:
            if record.get('resume_filename') == file.filename and record.get('ats_score') is not None:
                return jsonify({'score': record['ats_score'], 'feedback': record['ats_feedback']})

    prompt = f"""
    You are an ATS system evaluating a resume. 
    First line: return only a numeric score out of 100 like this format -> 85/100
    Second line: give brief feedback in 1 sentences and give attributes on what bases it has given that ats score like skill-50%,education-30% which make total 100

    Resume:
    {text}

    Score:
    """.strip()

    response = co.generate(
        model="command",
        prompt=prompt,
        max_tokens=100,
        temperature=0.5
    )

    output = response.generations[0].text.strip()
    lines = output.strip().splitlines()
    score = None
    feedback = ""

    for i, line in enumerate(lines):
        match = re.search(r'(\d{1,3})\s*/\s*100', line)
        if match:
            score = int(match.group(1))
            feedback_lines = lines[i+1:] if i + 1 < len(lines) else []
            feedback = ' '.join(feedback_lines).strip()
            break

    if score is None or not feedback:
        return jsonify({'error': 'AI did not return a valid score or feedback.', 'raw': output}), 500

    found = False
    for record in SESSION_DATA:
        if record['user'] == session['user']:
            record['ats_score'] = score
            record['ats_feedback'] = feedback
            record['resume_filename'] = file.filename
            found = True
            break

    if not found:
        SESSION_DATA.append({
            'user': session['user'],
            'resume_filename': file.filename,
            'interview_score': 0,
            'ats_score': score,
            'ats_feedback': feedback
        })

    return jsonify({'score': score, 'feedback': feedback})

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/')

    users = SESSION_DATA
    ats_scores = [u['ats_score'] for u in users if u.get('ats_score') is not None]
    interview_scores = [u['interview_score'] for u in users if u.get('interview_score') is not None]
    average_ats = round(sum(ats_scores) / len(ats_scores), 2) if ats_scores else 0
    highest_interview = max(interview_scores) if interview_scores else 0

    return render_template(
        'admin_dashboard.html',
        data=users,
        ats_scores=ats_scores,
        interview_scores=interview_scores,
        average_ats=average_ats,
        highest_interview=highest_interview
    )

@app.route('/download_pdf')
def download_pdf():
    if session.get('role') != 'admin':
        return redirect('/')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph("Admin Dashboard Report", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    data = [['User', 'Interview Score', 'ATS Score', 'Resume Filename']]

    for record in SESSION_DATA:
        row = [
            record['user'],
            f"{record['interview_score']}/50",
            record['ats_score'] if record['ats_score'] is not None else 'Pending',
            record.get('resume_filename', 'N/A')
        ]
        data.append(row)

    table = Table(data, colWidths=[100, 100, 80, 250])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="admin_dashboard_report.pdf", mimetype='application/pdf')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
