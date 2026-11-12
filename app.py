from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# --- Database setup ---
def init_db():
    conn = sqlite3.connect('ngos.db')
    c = conn.cursor()
    
    # 1. NGO Table
    c.execute('''CREATE TABLE IF NOT EXISTS ngos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  city TEXT NOT NULL,
                  service TEXT NOT NULL,
                  website_url TEXT NOT NULL,
                  category TEXT NOT NULL,
                  is_urgent INTEGER DEFAULT 0)''')
    
    # 2. Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  role TEXT NOT NULL)''')
                  
    # 3. Stats Table (Impact Meter)
    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (id INTEGER PRIMARY KEY,
                  support_count INTEGER DEFAULT 0)''')

    # 4. NEW: Volunteers Table
    c.execute('''CREATE TABLE IF NOT EXISTS volunteers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  ngo_id INTEGER,
                  name TEXT NOT NULL,
                  skills TEXT NOT NULL,
                  phone TEXT NOT NULL,
                  date_applied TEXT NOT NULL)''')
    
    # Initialize stats counter
    c.execute("INSERT OR IGNORE INTO stats (id, support_count) VALUES (1, 142)")
    
    # Create default admin
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', 'admin123', 'admin'))
        
    conn.commit()
    conn.close()

init_db()

# --- Helpers ---
def get_db_connection():
    conn = sqlite3.connect('ngos.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- Home page ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Impact Count
    c.execute("SELECT support_count FROM stats WHERE id=1")
    res = c.fetchone()
    impact_count = res['support_count'] if res else 0
    
    # Filters
    c.execute("SELECT DISTINCT city FROM ngos ORDER BY city ASC")
    cities = [row['city'] for row in c.fetchall()]
    c.execute("SELECT DISTINCT category FROM ngos ORDER BY category ASC")
    categories = [row['category'] for row in c.fetchall()]

    query = request.args.get('query', '').strip().lower()
    selected_city = request.args.get('city', '').strip().lower()
    selected_category = request.args.get('category', '').strip().lower()
    
    sql = "SELECT * FROM ngos WHERE 1=1"
    params = []
    
    if query:
        sql += " AND LOWER(name) LIKE ?"
        params.append(f"%{query}%")
    if selected_city:
        sql += " AND LOWER(city) = ?"
        params.append(selected_city)
    if selected_category:
        sql += " AND LOWER(category) = ?"
        params.append(selected_category)
        
    sql += " ORDER BY is_urgent DESC, id ASC" 
    c.execute(sql, params)
    ngos = c.fetchall()
    conn.close()
    
    role = session.get('role')
    return render_template('index.html', ngos=ngos, cities=cities, categories=categories,
                           query=query, selected_city=selected_city, selected_category=selected_category, 
                           role=role, impact_count=impact_count)

# --- Volunteer Routes ---
@app.route('/volunteer/<int:ngo_id>', methods=['GET', 'POST'])
def volunteer(ngo_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    ngo = conn.execute('SELECT * FROM ngos WHERE id = ?', (ngo_id,)).fetchone()
    
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        skills = request.form['skills']
        date_applied = datetime.now().strftime("%Y-%m-%d")
        
        conn.execute('INSERT INTO volunteers (user_id, ngo_id, name, skills, phone, date_applied) VALUES (?, ?, ?, ?, ?, ?)',
                     (session['user_id'], ngo_id, name, skills, phone, date_applied))
        conn.commit()
        
        # Get the ID of the new application for the certificate
        cur = conn.execute('SELECT last_insert_rowid()')
        app_id = cur.fetchone()[0]
        conn.close()
        
        flash('Application successful! You can now download your certificate.')
        return redirect(url_for('certificate', app_id=app_id))
    
    conn.close()
    return render_template('volunteer.html', ngo=ngo)

@app.route('/certificate/<int:app_id>')
def certificate(app_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    # Join tables to get NGO name and Volunteer details
    data = conn.execute('''
        SELECT v.name as vol_name, v.date_applied, n.name as ngo_name 
        FROM volunteers v 
        JOIN ngos n ON v.ngo_id = n.id 
        WHERE v.id = ?
    ''', (app_id,)).fetchone()
    conn.close()
    
    if data:
        return render_template('certificate.html', data=data)
    return "Certificate not found", 404

# --- Admin Routes ---
@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    ngos = conn.execute("SELECT * FROM ngos ORDER BY is_urgent DESC, id ASC").fetchall()
    
    # Stats
    total_ngos = len(ngos)
    cities = len(set([ngo['city'] for ngo in ngos])) if ngos else 0
    categories = len(set([ngo['category'] for ngo in ngos])) if ngos else 0
    
    conn.close()
    return render_template('admin.html', ngos=ngos, 
                           stats={'ngos': total_ngos, 'cities': cities, 'cats': categories})

@app.route('/manage_users')
def manage_users():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
    conn.close()
    return render_template('manage_users.html', users=users)

@app.route('/manage_volunteers')
def manage_volunteers():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    # Fetch volunteers with NGO names
    volunteers = conn.execute('''
        SELECT v.*, n.name as ngo_name 
        FROM volunteers v 
        JOIN ngos n ON v.ngo_id = n.id 
        ORDER BY v.date_applied DESC
    ''').fetchall()
    conn.close()
    return render_template('manage_volunteers.html', volunteers=volunteers)

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if session.get('role') != 'admin': return redirect(url_for('index'))
    if user_id == session.get('user_id'):
        flash("Cannot delete own admin account.")
        return redirect(url_for('manage_users'))
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_users'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if session.get('role') != 'admin': return redirect(url_for('index'))
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute("UPDATE users SET username=?, role=? WHERE id=?", 
                     (request.form['username'], request.form['role'], user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('manage_users'))
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return render_template('edit_user.html', user=user)

# --- Standard Routes (Add, Delete NGO, Login, Register, Impact) ---
@app.route('/add', methods=['POST'])
def add():
    if session.get('role') != 'admin': return redirect(url_for('index'))
    is_urgent = 1 if request.form.get('is_urgent') else 0
    conn = get_db_connection()
    conn.execute("INSERT INTO ngos (name, city, service, website_url, category, is_urgent) VALUES (?, ?, ?, ?, ?, ?)", 
                 (request.form['name'], request.form['city'], request.form['service'], request.form['website_url'], request.form['category'], is_urgent))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/delete/<int:ngo_id>')
def delete(ngo_id):
    if session.get('role') != 'admin': return redirect(url_for('index'))
    conn = get_db_connection()
    conn.execute("DELETE FROM ngos WHERE id=?", (ngo_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/track_click')
def track_click():
    conn = get_db_connection()
    conn.execute("UPDATE stats SET support_count = support_count + 1 WHERE id=1")
    conn.commit()
    conn.close()
    return ('', 204)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (request.form['username'], request.form['password'])).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('admin') if user['role'] == 'admin' else url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (request.form['username'], request.form['password'], 'user'))
            conn.commit()
            flash('Success! Login now.')
            return redirect(url_for('login'))
        except:
            flash('Username taken.')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)