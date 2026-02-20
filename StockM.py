import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, request, redirect, url_for, flash, session, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "stock_pro_secure_key_2026"

# --- CONFIGURATION & DATABASE ---
DB_NAME = "stockdata" 

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        created_date TEXT NOT NULL
    )''')
    admin = conn.execute("SELECT * FROM admins WHERE username='admin'").fetchone()
    if not admin:
        hashed_pw = generate_password_hash('admin123')
        conn.execute("INSERT INTO admins (username, password) VALUES (?,?)", ('admin', hashed_pw))
    conn.commit()
    conn.close()

# --- UI COMPONENTS ---
CSS = '''
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
<style>
    :root { --sidebar-bg: #0f172a; --accent: #6366f1; --bg: #f8fafc; }
    body { font-family: 'Inter', sans-serif; background-color: var(--bg); }
    .login-container { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }
    .login-card { width: 100%; max-width: 420px; border-radius: 24px; border: none; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); }
    .brand-logo { width: 60px; height: 60px; background: var(--accent); color: white; border-radius: 16px; display: inline-flex; align-items: center; justify-content: center; font-size: 2rem; margin-bottom: 1rem; }
    .sidebar { height: 100vh; background: var(--sidebar-bg); color: white; position: fixed; width: 260px; z-index: 100; }
    .main-content { margin-left: 260px; padding: 2.5rem; }
    .nav-link { color: #94a3b8; padding: 0.8rem 1.5rem; border-radius: 12px; margin: 0.3rem 1rem; transition: 0.2s; }
    .nav-link:hover, .nav-link.active { background: rgba(99, 102, 241, 0.15); color: #818cf8; }
    .nav-link.active { color: white; background: var(--accent); }
    .card { border: none; border-radius: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .stat-card { border-bottom: 4px solid var(--accent); }
    .low-stock { background-color: #fff1f2 !important; color: #e11d48; font-weight: 600; }
    .btn-primary { background: var(--accent); border: none; border-radius: 12px; font-weight: 600; }
    .calc-box { background: #f1f5f9; padding: 15px; border-radius: 12px; margin-top: 15px; border: 1px dashed #cbd5e1; }
</style>
'''

SIDEBAR = '''
<div class="sidebar d-flex flex-column shadow">
    <div class="p-4 mb-3">
        <h4 class="fw-black text-white d-flex align-items-center"><i class="bi bi-box-seam-fill me-2 text-primary"></i> StockPro</h4>
    </div>
    <ul class="nav flex-column mb-auto">
        <a href="/" class="nav-link {{ 'active' if active_page == 'dashboard' }}"><i class="bi bi-grid-1x2-fill me-2"></i> Dashboard</a>
        <a href="/products" class="nav-link {{ 'active' if active_page == 'products' }}"><i class="bi bi-archive-fill me-2"></i> Inventory</a>
        <a href="/add" class="nav-link {{ 'active' if active_page == 'add' }}"><i class="bi bi-plus-square-fill me-2"></i> Add Item</a>
    </ul>
    <div class="p-4">
        <a href="/logout" class="btn btn-outline-danger w-100 rounded-pill btn-sm"><i class="bi bi-power me-1"></i> Logout</a>
    </div>
</div>
'''

FLASH_MSG = '''
{% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}{% for cat, msg in messages %}
        <div class="alert alert-{{ cat }} border-0 shadow-sm alert-dismissible fade show mb-4">{{ msg }}<button class="btn-close" data-bs-dismiss="alert"></button></div>
    {% endfor %}{% endif %}
{% endwith %}
'''

# --- CALCULATION SCRIPT ---
CALC_JS = '''
<script>
    function updateCalc() {
        const qty = document.getElementById('qty-input').value || 0;
        const price = document.getElementById('price-input').value || 0;
        const total = (qty * price).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
        document.getElementById('total-val').innerText = '$' + total;
    }
</script>
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        conn = get_db()
        admin = conn.execute("SELECT * FROM admins WHERE username = ?", (user,)).fetchone()
        conn.close()
        if admin and check_password_hash(admin['password'], pw):
            session['admin'] = user
            return redirect(url_for('dashboard'))
    
    html = f'''{CSS}
    <div class="login-container">
        <div class="card login-card p-5 bg-white">
            <div class="text-center mb-4">
                <div class="brand-logo shadow-lg"><i class="bi bi-box-seam-fill"></i></div>
                <h2 class="fw-bold text-dark">StockPro</h2>
                <p class="text-muted">Inventory Management System</p>
            </div>
            {FLASH_MSG}
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label small fw-bold text-muted">Username</label>
                    <input name="username" class="form-control form-control-lg bg-light border px-4 rounded-4" style="border-color: #dee2e6 !important;" required>
                </div>
                <div class="mb-4">
                    <label class="form-label small fw-bold text-muted">Password</label>
                    <input name="password" type="password" class="form-control form-control-lg bg-light border px-4 rounded-4" style="border-color: #dee2e6 !important;" required>
                </div>
                <button class="btn btn-primary w-100 py-3 rounded-4 shadow-lg">Sign In</button>
            </form>
        </div>
    </div>'''
    return render_template_string(html)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    if 'admin' not in session: return redirect(url_for('login'))
    conn = get_db()
    total_items = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    total_qty = conn.execute("SELECT SUM(quantity) FROM inventory").fetchone()[0] or 0
    low_stock = conn.execute("SELECT COUNT(*) FROM inventory WHERE quantity < 5").fetchone()[0]
    rows = conn.execute("SELECT product_name, quantity, category FROM inventory").fetchall()
    conn.close()
    cat_map = {}
    for r in rows: cat_map[r['category']] = cat_map.get(r['category'], 0) + r['quantity']

    html = f'''{CSS}{SIDEBAR.replace('{{ active_page == "dashboard" }}', 'active')}
    <div class="main-content">
        <h2 class="fw-bold mb-4">Dashboard</h2>
        <div class="row g-4 mb-5">
            <div class="col-md-4"><div class="card p-4 stat-card border-primary"><h6>Total Products</h6><h2 class="fw-bold text-primary">{{{{ total_items }}}}</h2></div></div>
            <div class="col-md-4"><div class="card p-4 stat-card border-success"><h6>Total Stock Quantity</h6><h2 class="fw-bold text-success">{{{{ total_qty }}}}</h2></div></div>
            <div class="col-md-4"><div class="card p-4 stat-card border-danger"><h6>Low Stock Items</h6><h2 class="fw-bold text-danger">{{{{ low_stock }}}}</h2></div></div>
        </div>
        <div class="row g-4">
            <div class="col-md-8"><div class="card p-4 h-100 shadow-sm"><canvas id="barChart"></canvas></div></div>
            <div class="col-md-4"><div class="card p-4 h-100 shadow-sm"><canvas id="pieChart"></canvas></div></div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const barCtx = document.getElementById('barChart').getContext('2d');
        new Chart(barCtx, {{ type: 'bar', data: {{ labels: {json.dumps([r['product_name'] for r in rows])}, datasets: [{{ label: 'Quantity', data: {json.dumps([r['quantity'] for r in rows])}, backgroundColor: '#6366f1', borderRadius: 8 }}] }} }});
        const pieCtx = document.getElementById('pieChart').getContext('2d');
        new Chart(pieCtx, {{ type: 'doughnut', data: {{ labels: {json.dumps(list(cat_map.keys()))}, datasets: [{{ data: {json.dumps(list(cat_map.values()))}, backgroundColor: ['#6366f1', '#10b981', '#f59e0b', '#ef4444'] }}] }} }});
    </script>'''
    return render_template_string(html, total_items=total_items, total_qty=total_qty, low_stock=low_stock, active_page='dashboard')

@app.route('/products')
def products():
    if 'admin' not in session: return redirect(url_for('login'))
    search = request.args.get('search', '')
    conn = get_db()
    items = conn.execute("SELECT * FROM inventory WHERE product_name LIKE ?", ('%'+search+'%',)).fetchall()
    conn.close()
    html = f'''{CSS}{SIDEBAR.replace('{{ active_page == "products" }}', 'active')}
    <div class="main-content">
        <div class="d-flex justify-content-between mb-4"><h2>Inventory</h2><form class="d-flex w-25"><input name="search" class="form-control me-2" value="{{{{ search }}}}"/><button class="btn btn-primary"><i class="bi bi-search"></i></button></form></div>
        <div class="card border-0 shadow-sm overflow-hidden"><table class="table table-hover align-middle mb-0"><thead class="table-light"><tr><th class="px-4 py-3">ID</th><th>Product</th><th>Category</th><th>Qty</th><th>Price</th><th>Actions</th></tr></thead><tbody>
            {{% for i in items %}}<tr class="{{ 'low-stock' if i.quantity < 5 else '' }}"><td class="px-4">#{{{{ i.id }}}}</td><td class="fw-bold">{{{{ i.product_name }}}}</td><td>{{{{ i.category }}}}</td><td>{{{{ i.quantity }}}}</td><td>${{{{ "%.2f"|format(i.price) }}}}</td><td class="text-center">
            <a href="/edit/{{{{ i.id }}}}" class="btn btn-sm btn-light text-primary"><i class="bi bi-pencil-fill"></i></a>
            <a href="/delete/{{{{ i.id }}}}" class="btn btn-sm btn-light text-danger" onclick="return confirm('Delete?')"><i class="bi bi-trash-fill"></i></a></td></tr>{{% endfor %}}</tbody></table></div></div>'''
    return render_template_string(html, items=items, search=search, active_page='products')

@app.route('/add', methods=['GET', 'POST'])
def add():
    if 'admin' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        name, cat, qty, pr = request.form['name'], request.form['category'], request.form['qty'], request.form['price']
        conn = get_db()
        conn.execute("INSERT INTO inventory (product_name, category, quantity, price, created_date) VALUES (?,?,?,?,?)",
                     (name, cat, qty, pr, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit(); conn.close()
        return redirect(url_for('products'))
    html = f'''{CSS}{SIDEBAR.replace('{{ active_page == "add" }}', 'active')}
    <div class="main-content"><div class="card p-5 shadow-lg border-0 mx-auto" style="max-width: 600px;"><h3>New Item</h3>
    <form method="POST"><div class="mb-3"><label>Product Name</label><input name="name" class="form-control bg-light" required></div>
    <div class="mb-3"><label>Category</label><input name="category" class="form-control bg-light" required></div>
    <div class="row"><div class="col-6"><label>Quantity</label><input id="qty-input" name="qty" type="number" class="form-control bg-light" oninput="updateCalc()" required></div>
    <div class="col-6"><label>Price ($)</label><input id="price-input" name="price" type="number" step="0.01" class="form-control bg-light" oninput="updateCalc()" required></div></div>
    <div class="calc-box"><div class="small fw-bold text-muted">ESTIMATED STOCK VALUE</div><h3 id="total-val" class="mb-0 text-primary">$0.00</h3></div>
    <button class="btn btn-primary w-100 py-3 mt-4">Save Item</button></form></div></div>{CALC_JS}'''
    return render_template_string(html, active_page='add')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if 'admin' not in session: return redirect(url_for('login'))
    conn = get_db()
    item = conn.execute("SELECT * FROM inventory WHERE id = ?", (id,)).fetchone()
    if request.method == 'POST':
        conn.execute("UPDATE inventory SET product_name=?, category=?, quantity=?, price=? WHERE id=?",
                     (request.form['name'], request.form['category'], request.form['qty'], request.form['price'], id))
        conn.commit(); conn.close()
        return redirect(url_for('products'))
    html = f'''{CSS}{SIDEBAR}<div class="main-content"><div class="card p-5 shadow-lg border-0 mx-auto" style="max-width: 600px;"><h3>Edit Item #{{{{ item.id }}}}</h3>
    <form method="POST"><div class="mb-3"><label>Product Name</label><input name="name" class="form-control bg-light" value="{{{{ item.product_name }}}}" required></div>
    <div class="mb-3"><label>Category</label><input name="category" class="form-control bg-light" value="{{{{ item.category }}}}" required></div>
    <div class="row"><div class="col-6"><label>Quantity</label><input id="qty-input" name="qty" type="number" class="form-control bg-light" value="{{{{ item.quantity }}}}" oninput="updateCalc()" required></div>
    <div class="col-6"><label>Price ($)</label><input id="price-input" name="price" type="number" step="0.01" class="form-control bg-light" value="{{{{ item.price }}}}" oninput="updateCalc()" required></div></div>
    <div class="calc-box"><div class="small fw-bold text-muted">ESTIMATED STOCK VALUE</div><h3 id="total-val" class="mb-0 text-primary">${{{{ "%.2f"|format(item.price * item.quantity) }}}}</h3></div>
    <button class="btn btn-primary w-100 py-3 mt-4">Update Item</button></form></div></div>{CALC_JS}'''
    return render_template_string(html, item=item, active_page='products')

@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db(); conn.execute("DELETE FROM inventory WHERE id = ?", (id,)); conn.commit(); conn.close()
    return redirect(url_for('products'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)