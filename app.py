from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
import sqlite3, hashlib, os, csv, io
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)
DB = 'database/profit.db'

# ── DB helpers ────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                cost_price REAL DEFAULT 0,
                selling_price REAL DEFAULT 0,
                ad_spend REAL DEFAULT 0,
                platform_fees REAL DEFAULT 0,
                delivery_cost REAL DEFAULT 0,
                return_rate REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        """)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def calc_profit(p):
    return_loss = p['selling_price'] * (p['return_rate'] / 100)
    total_cost = p['cost_price'] + p['ad_spend'] + p['platform_fees'] + p['delivery_cost'] + return_loss
    profit = p['selling_price'] - total_cost
    margin = (profit / p['selling_price'] * 100) if p['selling_price'] > 0 else 0
    return round(profit, 2), round(margin, 2)

# ── Auth decorator ─────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username=? AND password=?',
                          (data['username'], hash_pw(data['password']))).fetchone()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({'ok': True})
        return jsonify({'ok': False, 'error': 'Invalid credentials'}), 401
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    try:
        with get_db() as db:
            db.execute('INSERT INTO users (username, password) VALUES (?,?)',
                       (data['username'], hash_pw(data['password'])))
        return jsonify({'ok': True})
    except sqlite3.IntegrityError:
        return jsonify({'ok': False, 'error': 'Username already exists'}), 409

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── Page routes ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session['username'])

@app.route('/products')
@login_required
def products_page():
    return render_template('products.html', username=session['username'])

@app.route('/reports')
@login_required
def reports_page():
    return render_template('reports.html', username=session['username'])

# ── API: products ──────────────────────────────────────────────────────────────

@app.route('/api/products', methods=['GET'])
@login_required
def get_products():
    db = get_db()
    rows = db.execute('SELECT * FROM products WHERE user_id=? ORDER BY created_at DESC',
                      (session['user_id'],)).fetchall()
    result = []
    for r in rows:
        p = dict(r)
        p['profit'], p['margin'] = calc_profit(p)
        result.append(p)
    return jsonify(result)

@app.route('/api/products', methods=['POST'])
@login_required
def add_product():
    d = request.get_json()
    with get_db() as db:
        cur = db.execute(
            'INSERT INTO products (user_id,name,cost_price,selling_price,ad_spend,platform_fees,delivery_cost,return_rate) VALUES (?,?,?,?,?,?,?,?)',
            (session['user_id'], d['name'], d['cost_price'], d['selling_price'],
             d['ad_spend'], d['platform_fees'], d['delivery_cost'], d['return_rate'])
        )
        pid = cur.lastrowid
    p = dict(get_db().execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone())
    p['profit'], p['margin'] = calc_profit(p)
    return jsonify(p), 201

@app.route('/api/products/<int:pid>', methods=['PUT'])
@login_required
def update_product(pid):
    d = request.get_json()
    with get_db() as db:
        db.execute(
            'UPDATE products SET name=?,cost_price=?,selling_price=?,ad_spend=?,platform_fees=?,delivery_cost=?,return_rate=? WHERE id=? AND user_id=?',
            (d['name'], d['cost_price'], d['selling_price'], d['ad_spend'],
             d['platform_fees'], d['delivery_cost'], d['return_rate'], pid, session['user_id'])
        )
    p = dict(get_db().execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone())
    p['profit'], p['margin'] = calc_profit(p)
    return jsonify(p)

@app.route('/api/products/<int:pid>', methods=['DELETE'])
@login_required
def delete_product(pid):
    with get_db() as db:
        db.execute('DELETE FROM products WHERE id=? AND user_id=?', (pid, session['user_id']))
    return jsonify({'ok': True})

# ── API: dashboard stats ───────────────────────────────────────────────────────

@app.route('/api/stats')
@login_required
def get_stats():
    db = get_db()
    rows = db.execute('SELECT * FROM products WHERE user_id=?', (session['user_id'],)).fetchall()
    products = []
    for r in rows:
        p = dict(r)
        p['profit'], p['margin'] = calc_profit(p)
        products.append(p)
    total_profit = sum(p['profit'] for p in products)
    loss_count = sum(1 for p in products if p['profit'] < 0)
    top = max(products, key=lambda p: p['profit']) if products else None
    return jsonify({
        'total_profit': round(total_profit, 2),
        'total_products': len(products),
        'loss_count': loss_count,
        'top_product': top['name'] if top else '—',
        'top_profit': top['profit'] if top else 0,
        'chart_labels': [p['name'] for p in products],
        'chart_profits': [p['profit'] for p in products],
    })

# ── API: what-if ───────────────────────────────────────────────────────────────

@app.route('/api/whatif/<int:pid>', methods=['POST'])
@login_required
def whatif(pid):
    d = request.get_json()
    db = get_db()
    row = db.execute('SELECT * FROM products WHERE id=? AND user_id=?', (pid, session['user_id'])).fetchone()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    p = dict(row)
    p['ad_spend'] = float(d.get('ad_spend', p['ad_spend']))
    profit, margin = calc_profit(p)
    return jsonify({'profit': profit, 'margin': margin})

# ── API: CSV export ────────────────────────────────────────────────────────────

@app.route('/api/export')
@login_required
def export_csv():
    db = get_db()
    rows = db.execute('SELECT * FROM products WHERE user_id=?', (session['user_id'],)).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name','Cost Price','Selling Price','Ad Spend','Platform Fees','Delivery Cost','Return Rate (%)','Profit','Margin (%)'])
    for r in rows:
        p = dict(r)
        profit, margin = calc_profit(p)
        writer.writerow([p['name'], p['cost_price'], p['selling_price'], p['ad_spend'],
                         p['platform_fees'], p['delivery_cost'], p['return_rate'], profit, margin])
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=profit_report.csv'})

# ── Seed sample data ───────────────────────────────────────────────────────────

@app.route('/api/seed')
@login_required
def seed():
    samples = [
        ('Wireless Earbuds', 18, 59.99, 12, 4.5, 3.5, 8),
        ('Phone Case', 2.5, 14.99, 6, 1.5, 2, 15),
        ('LED Desk Lamp', 12, 34.99, 8, 3, 4, 5),
        ('Yoga Mat', 8, 29.99, 14, 3.5, 5, 12),
        ('Bluetooth Speaker', 22, 49.99, 18, 4, 5, 10),
    ]
    with get_db() as db:
        for s in samples:
            db.execute('INSERT INTO products (user_id,name,cost_price,selling_price,ad_spend,platform_fees,delivery_cost,return_rate) VALUES (?,?,?,?,?,?,?,?)',
                       (session['user_id'], *s))
    return jsonify({'ok': True})

if __name__ == '__main__':
    os.makedirs('database', exist_ok=True)
    init_db()
    import os

port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
