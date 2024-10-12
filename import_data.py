import json
from werkzeug.security import generate_password_hash
from app import db, Student, Statement, StatementChoice, Teacher

def import_students():
    with open('students.json') as f:
        students = json.load(f)
        for student in students:
            existing_student = Student.query.filter_by(student_number=student['student_number']).first()
            if existing_student:
                print(f"Student with student_number {student['student_number']} already exists. Skipping.")
                continue
            new_student = Student(
                student_number=student['student_number'],
                name=student['student_name'],
                class_name=student['student_class'],
                team=None
            )
            db.session.add(new_student)
        db.session.commit()

def import_statements():
    with open('actiontype_statements.json') as f:
        statements = json.load(f)
        for statement in statements:
            new_statement = Statement(
                statement_number=statement['statement_number']
            )
            db.session.add(new_statement)
            db.session.commit() 

            for choice in statement['statement_choices']:
                new_choice = StatementChoice(
                    statement_id=new_statement.id,
                    choice_number=choice['choice_number'],
                    choice_text=choice['choice_text'],
                    choice_result=choice['choice_result']
                )
                db.session.add(new_choice)
        db.session.commit()

def create_teachers():
    teacher1 = Teacher(
        username='teacher1',
        password=generate_password_hash('password1', method='pbkdf2:sha256'),
        is_admin=True
    )
    
    teacher2 = Teacher(
        username='teacher2',
        password=generate_password_hash('password2', method='pbkdf2:sha256'),
        is_admin=False
    )
    
    db.session.add(teacher1)
    db.session.add(teacher2)
    db.session.commit()

if __name__ == '__main__':
    from app import app
    with app.app_context():
        db.create_all()
        import_students()
        import_statements()
        create_teachers()