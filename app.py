from flask import Flask, render_template, request, redirect, send_file
import pickle
import pandas as pd
import sqlite3

app = Flask(__name__)

model = pickle.load(open('model.pkl', 'rb'))


def get_db_data(search=""):
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    if search:
        cursor.execute(
            "SELECT * FROM predictions WHERE name LIKE ? ORDER BY id DESC",
            ('%' + search + '%',)
        )
    else:
        cursor.execute(
            "SELECT * FROM predictions ORDER BY id DESC"
        )

    data = cursor.fetchall()
    conn.close()
    return data


@app.route('/')
def home():
    return render_template(
        'index.html',
        prediction_text=None,
        errors=[]
    )


@app.route('/dashboard')
def dashboard():
    history = get_db_data()
    return render_template(
        'dashboard.html',
        history=history
    )


@app.route('/predict', methods=['POST'])
def predict():

    try:

        name = request.form['name'].strip()
        hours = float(request.form['hours'])
        attendance = float(request.form['attendance'])
        sleep = float(request.form['sleep'])
        midsem = float(request.form['midsem'])

        errors = []

        # Validation
        if hours < 1 or hours > 24:
            errors.append(
                "Study hours must be between 1 and 24"
            )

        if sleep < 1 or sleep > 24:
            errors.append(
                "Sleep hours must be between 1 and 24"
            )

        if midsem < 0 or midsem > 20:
            errors.append(
                "Mid-sem marks must be between 0 and 20"
            )

        if attendance < 0 or attendance > 100:
            errors.append(
                "Attendance must be between 0 and 100%"
            )

        if name == "":
            errors.append(
                "Student name is required"
            )

        # Show all errors together
        if errors:
            return render_template(
                'index.html',
                errors=errors,
                prediction_text=None
            )

        # Prediction
        input_data = pd.DataFrame(
            [[hours, attendance, sleep, midsem]],
            columns=[
                'hours',
                'attendance',
                'sleep',
                'midsem'
            ]
        )

        prediction = model.predict(input_data)
        marks = round(prediction[0], 2)

        if marks > 100:
            marks = 100

        if marks < 0:
            marks = 0

        # Grade logic
        if marks >= 90:
            grade = "A+"
            status = "PASS ✅"
            advice = "Excellent performance. Keep going."

        elif marks >= 75:
            grade = "A"
            status = "PASS ✅"
            advice = "Very good performance."

        elif marks >= 60:
            grade = "B"
            status = "PASS ✅"
            advice = "Good performance."

        elif marks >= 40:
            grade = "C"
            status = "PASS ✅"
            advice = "Average performance."

        else:
            grade = "F"
            status = "FAIL ❌"
            advice = "Needs improvement."

        # Save to database
        conn = sqlite3.connect('students.db')
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO predictions
        (name,hours,attendance,sleep,midsem,predicted_marks,grade,status)
        VALUES (?,?,?,?,?,?,?,?)
        ''',
        (
            name,
            hours,
            attendance,
            sleep,
            midsem,
            marks,
            grade,
            status
        ))

        conn.commit()
        conn.close()

        return render_template(
            'index.html',
            prediction_text=marks,
            grade=grade,
            status=status,
            advice=advice,
            progress=int(marks),
            errors=[]
        )

    except Exception as e:

        return render_template(
            'index.html',
            prediction_text=None,
            errors=[f"Error: {str(e)}"]
        )


@app.route('/search', methods=['POST'])
def search():

    keyword = request.form['keyword']
    history = get_db_data(keyword)

    return render_template(
        'dashboard.html',
        history=history
    )


@app.route('/delete/<int:id>')
def delete(id):

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM predictions WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect('/dashboard')


@app.route('/export')
def export():

    conn = sqlite3.connect('students.db')

    df = pd.read_sql_query(
        "SELECT * FROM predictions",
        conn
    )

    df.to_csv(
        "student_predictions.csv",
        index=False
    )

    conn.close()

    return send_file(
        "student_predictions.csv",
        as_attachment=True
    )


if __name__ == "__main__":
    app.run(debug=True)