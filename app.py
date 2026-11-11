from flask import Flask, render_template, request, redirect, session
import psycopg2

app = Flask(__name__)
app.secret_key = 'super_secret_key'

def get_db():
    conn = psycopg2.connect(
        host="localhost",
        database="conference_db",
        user="postgres",
        password="admin123",  # <--- ТВОЙ ПАРОЛЬ ОТ POSTGRESQL!
        port="5432"
    )
    return conn

# --- РЕГИСТРАЦИЯ ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        full_name = request.form['full_name']
        phone = request.form['phone']
        email = request.form['email']

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (login, password, full_name, phone, email) VALUES (%s, %s, %s, %s, %s)",
                (login, password, full_name, phone, email)
            )
            conn.commit()
            return "<h2>Пользователь создан!</h2><a href='/login'>Перейти ко входу</a>"
        except Exception as e:
            conn.rollback()
            return f"<h2>Ошибка: {e}</h2><a href='/register'>Назад</a>"
        finally:
            cur.close()
            conn.close()
    return render_template('register.html')

# --- АВТОРИЗАЦИЯ ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        login_input = request.form['login']
        password_input = request.form['password']

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, login FROM users WHERE login = %s AND password = %s", (login_input, password_input))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['login'] = user[1]
            return redirect('/my_requests')
        else:
            error = "Неверный логин или пароль!"
    return render_template('login.html', error=error)

# --- ЛИЧНЫЙ КАБИНЕТ ---
@app.route('/my_requests')
def my_requests():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.id, rm.name, r.start_date, r.payment_method, r.status 
        FROM requests r 
        JOIN rooms rm ON r.room_id = rm.id 
        WHERE r.user_id = %s
    """, (session['user_id'],))
    requests_list = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('my_requests.html', requests=requests_list, login=session['login'])

# --- СОЗДАНИЕ ЗАЯВКИ ---
@app.route('/create_request', methods=['GET', 'POST'])
def create_request():
    if 'user_id' not in session:
        return redirect('/login')

    error = None
    if request.method == 'POST':
        room_name = request.form['room_name']
        start_date = request.form['start_date']
        payment_method = request.form['payment_method']

        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM rooms WHERE name = %s", (room_name,))
        room = cur.fetchone()
        
        if room:
            room_id = room[0]
            cur.execute(
                "INSERT INTO requests (user_id, room_id, start_date, payment_method, status) VALUES (%s, %s, %s, %s, 'Новая')",
                (session['user_id'], room_id, start_date, payment_method)
            )
            conn.commit()
            cur.close()
            conn.close()
            return redirect('/my_requests')
        else:
            error = "Помещение с таким названием не найдено!"
            cur.close()
            conn.close()

    return render_template('create_request.html', error=error)

# --- ПАНЕЛЬ АДМИНИСТРАТОРА (ВХОД) ---
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        
        # Жестко заданные логин и пароль из задания
        if login == 'Conf2027' and password == 'Demo77':
            session['is_admin'] = True
            return redirect('/admin_requests')
        else:
            error = "Неверный логин или пароль администратора!"
            
    return render_template('admin_login.html', error=error)

# --- ПАНЕЛЬ АДМИНИСТРАТОРА (ВСЕ ЗАЯВКИ) ---
@app.route('/admin_requests')
def admin_requests():
    if not session.get('is_admin'):
        return redirect('/admin_login')

    conn = get_db()
    cur = conn.cursor()
    # Достаем ВСЕ заявки из базы, плюс логин пользователя
    cur.execute("""
        SELECT r.id, u.login, rm.name, r.start_date, r.payment_method, r.status 
        FROM requests r 
        JOIN rooms rm ON r.room_id = rm.id 
        JOIN users u ON r.user_id = u.id
    """)
    all_requests = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('admin_requests.html', requests=all_requests)

# --- ИЗМЕНЕНИЕ СТАТУСА ЗАЯВКИ ---
@app.route('/update_status/<int:req_id>/<string:new_status>')
def update_status(req_id, new_status):
    if not session.get('is_admin'):
        return redirect('/admin_login')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE requests SET status = %s WHERE id = %s", (new_status, req_id))
    conn.commit()
    cur.close()
    conn.close()

    return redirect('/admin_requests')
# --- ДОБАВЛЕНИЕ ОТЗЫВА ---
@app.route('/add_review/<int:req_id>', methods=['POST'])
def add_review(req_id):
    if 'user_id' not in session:
        return redirect('/login')

    review_text = request.form['review_text']
    
    conn = get_db()
    cur = conn.cursor()
    # Добавляем отзыв в базу (оценку ставим 5 по умолчанию для простоты)
    cur.execute(
        "INSERT INTO reviews (user_id, request_id, text, rating) VALUES (%s, %s, %s, 5)",
        (session['user_id'], req_id, review_text)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect('/my_requests')
if __name__ == '__main__':
    app.run(debug=True)