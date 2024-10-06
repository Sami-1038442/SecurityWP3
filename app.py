import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Student, Statement, StatementChoice, Answer, Teacher
from datetime import timedelta
from flask_session import Session

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///action_types.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

db.init_app(app)
Session(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Teacher.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Teacher.query.filter_by(username=username).first()
        if user is None or not check_password_hash(user.password, password):
            flash('Verkeerde gebruikersnaam of wachtwoord')
            return redirect(url_for('login'))
        
        login_user(user)
        return redirect(url_for('admin'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        class_name = request.form.get('class_name')
        team_name = request.form.get('team_name')

        query = Student.query
        if class_name:
            query = query.filter_by(class_name=class_name)
        if team_name:
            query = query.filter_by(team=team_name)

        students = query.all()
    else:
        students = Student.query.all()

    teachers = Teacher.query.all()
    return render_template('admin.html', students=students, teachers=teachers, is_admin=current_user.is_admin)

@app.route('/api/admin/add_student', methods=['POST'])
@login_required
def add_student():
    data = request.get_json()
    student_number = data.get('student_number')
    name = data.get('name')
    class_name = data.get('class_name')

    if not student_number or not name or not class_name:
        return jsonify({"error": "Missing data"}), 400

    new_student = Student(student_number=student_number, name=name, class_name=class_name)
    db.session.add(new_student)
    db.session.commit()

    return jsonify({"result": "ok"})

@app.route('/api/admin/delete_student/<student_number>', methods=['DELETE'])
@login_required
def delete_student(student_number):
    student = Student.query.filter_by(student_number=student_number).first()
    if not student:
        return jsonify({"error": "Dit studentnummer is niet geregistreerd"}), 404

    Answer.query.filter_by(student_id=student.id).delete()
    db.session.delete(student)
    db.session.commit()

    return jsonify({"result": "ok"})

@app.route('/student_details/<student_number>', methods=['GET'])
@login_required
def student_details(student_number):
    student = Student.query.filter_by(student_number=student_number).first()
    if not student:
        flash("Student niet gevonden.", "error")
        return redirect(url_for('admin'))
    
    return render_template('student_details.html', student=student)

@app.route('/api/admin/student/<student_number>', methods=['GET'])
@login_required
def get_student_details(student_number):
    student = Student.query.filter_by(student_number=student_number).first()
    if not student:
        return jsonify({"error": "Dit studentnummer is niet geregistreerd"}), 404

    response = {
        "student_number": student.student_number,
        "name": student.name,
        "class_name": student.class_name,
        "team": student.team,
        "added_by": current_user.username,
        "answers": [
            {
                "statement_number": answer.statement_id,
                "choice": answer.choice
            } for answer in student.answers
        ]
    }

    return jsonify(response)

@app.route('/api/admin/student/<student_number>/edit', methods=['POST'])
@login_required
def edit_student(student_number):
    data = request.get_json()
    student = Student.query.filter_by(student_number=student_number).first()

    if not student:
        return jsonify({"error": "Student niet gevonden"}), 404

    student.name = data.get('name', student.name)
    student.class_name = data.get('class_name', student.class_name)
    student.team = data.get('team', student.team)

    db.session.commit()

    return jsonify({"result": "ok"})

@app.route('/api/admin/add_teacher', methods=['POST'])
@login_required
def add_teacher():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False)

    if not username or not password:
        return jsonify({"error": "Missing data"}), 400

    new_teacher = Teacher(username=username, password=generate_password_hash(password, method='pbkdf2:sha256', salt_length=16, iterations=100000), is_admin=is_admin)
    db.session.add(new_teacher)
    db.session.commit()

    return jsonify({"result": "ok"})

@app.route('/api/admin/delete_teacher/<teacher_id>', methods=['DELETE'])
@login_required
def delete_teacher(teacher_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404

    db.session.delete(teacher)
    db.session.commit()

    return jsonify({"result": "ok"})

@app.route('/statements')
def statements():
    student_number = request.args.get('student_number')
    return render_template('statements.html', student_number=student_number)

@app.route('/api/student/<student_number>/statement', methods=['GET'])
def get_statement(student_number):
    student = Student.query.filter_by(student_number=student_number).first()
    if not student:
        return jsonify({"error": "Dit studentnummer is niet geregistreerd"}), 404

    answered_statements = [answer.statement_id for answer in student.answers]
    next_statement = Statement.query.filter(~Statement.id.in_(answered_statements)).first()

    if not next_statement:
        action_type = calculate_action_type(student)
        return jsonify({"error": f"Je hebt de test al afgerond. Jouw actiontype is {action_type}!"}), 200

    response = {
        "statement_number": next_statement.statement_number,
        "statement_choices": [
            {
                "choice_number": choice.choice_number,
                "choice_text": choice.choice_text
            } for choice in next_statement.choices
        ]
    }
    return jsonify(response)

@app.route('/api/student/<student_number>/statement/<statement_number>', methods=['POST'])
def save_answer(student_number, statement_number):
    data = request.get_json()
    choice_number = data.get('statement_choice')

    student = Student.query.filter_by(student_number=student_number).first()
    if not student:
        return jsonify({"error": "Dit studentnummer is niet geregistreerd"}), 404

    statement = Statement.query.filter_by(statement_number=statement_number).first()
    if not statement:
        return jsonify({"error": "Statement not found"}), 404

    choice = StatementChoice.query.filter_by(statement_id=statement.id, choice_number=choice_number).first()
    if not choice:
        return jsonify({"error": "Choice not found"}), 404

    answer = Answer(student_id=student.id, statement_id=statement.id, choice=choice_number)
    db.session.add(answer)
    db.session.commit()

    total_statements = Statement.query.count()
    answered_statements = len(student.answers)
    if answered_statements == total_statements:
        action_type = calculate_action_type(student)
        student.action_type = action_type
        db.session.commit()
        return jsonify({"result": "ok", "action_type": action_type})

    return jsonify({"result": "ok"})

def create_database():
    with app.app_context():
        db.create_all()

def calculate_action_type(student):
    characteristics = {
        "E": 0, "I": 0, 
        "S": 0, "N": 0, 
        "T": 0, "F": 0,  
        "J": 0, "P": 0   
    }

    for answer in student.answers:
        choice = StatementChoice.query.filter_by(statement_id=answer.statement_id, choice_number=answer.choice).first()
        if choice.choice_result in characteristics:
            characteristics[choice.choice_result] += 1

    action_type = ""
    action_type += "I" if characteristics["I"] > characteristics["E"] else "E"
    action_type += "N" if characteristics["N"] > characteristics["S"] else "S"
    action_type += "F" if characteristics["F"] > characteristics["T"] else "T"
    action_type += "P" if characteristics["P"] > characteristics["J"] else "J"

    return action_type

if __name__ == '__main__':
    create_database()
    app.run(debug=True)
