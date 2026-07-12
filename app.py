import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, redirect, render_template_string, request, session, url_for, Response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'expenses.db')
app.secret_key = 'expense-tracker-secret-key'

HTML_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Expense Tracker</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; background: #f5f7fb; color: #111827; }
      nav { margin-bottom: 1rem; }
      nav a { margin-right: 1rem; text-decoration: none; color: #2563eb; font-weight: bold; }
      .card { background: white; padding: 1.2rem; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 1rem; }
      .summary { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
      .summary div { background: #eff6ff; padding: 1rem; border-radius: 10px; min-width: 180px; }
      table { width: 100%; border-collapse: collapse; background: white; }
      th, td { padding: 0.7rem; border-bottom: 1px solid #eee; text-align: left; }
      form input { display: block; margin-bottom: 0.7rem; padding: 0.6rem; width: 100%; max-width: 320px; }
      button { background: #2563eb; color: white; border: none; padding: 0.7rem 1rem; border-radius: 8px; cursor: pointer; }
      .small { font-size: 0.9rem; color: #4b5563; }
    </style>
  </head>
  <body>
    <nav>
      <a href="/">Dashboard</a>
      <a href="/add">Add Expense</a>
      <a href="/recurring">Recurring</a>
      <a href="/export-csv">Export CSV</a>
      <a href="/logout">Logout</a>
    </nav>
    <h1>Expense Dashboard</h1>
    <p class="small">Signed in as {{ username }} — shared household view</p>
    <div class="summary">
      <div><strong>Total Spent</strong><br>${{ total_spent }}</div>
      <div><strong>Entries</strong><br>{{ entry_count }}</div>
      <div><strong>Categories</strong><br>{{ category_count }}</div>
    </div>
    <div class="card">
      <h3>Recent Expenses</h3>
      <table>
        <tr><th>Spender</th><th>Date</th><th>Description</th><th>Category</th><th>Subcategory</th><th>Amount</th><th>Actions</th></tr>
        {% for expense in expenses %}
        <tr>
          <td>{{ expense['spender_username'] or 'Unknown' }}</td>
          <td>{{ expense['expense_date'] }}</td>
          <td>{{ expense['description'] }}</td>
          <td>{{ expense['category_name'] or 'Uncategorized' }}</td>
          <td>{{ expense['subcategory_name'] or '-' }}</td>
          <td>${{ '%.2f'|format(expense['price']) }}</td>
          <td>
            <a href="/edit-expense/{{ expense['id'] }}">Edit</a> |
            <form method="post" action="/delete-expense/{{ expense['id'] }}" style="display:inline;">
              <button type="submit">Delete</button>
            </form>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="7">No expenses yet. Add your first one.</td></tr>
        {% endfor %}
      </table>
    </div>
    <div class="card">
      <h3>Monthly Totals</h3>
      <ul>
        {% for month in monthly_totals %}
        <li>{{ month['month'] }}: ${{ '%.2f'|format(month['total']) }}</li>
        {% else %}
        <li>No spending data yet.</li>
        {% endfor %}
      </ul>
    </div>
    <div class="card">
      <h3>Category Spend</h3>
      <ul>
        {% for row in category_totals %}
        <li>{{ row['category'] }}: ${{ '%.2f'|format(row['total']) }}</li>
        {% else %}
        <li>No category data yet.</li>
        {% endfor %}
      </ul>
    </div>
  </body>
</html>
"""

ADD_EXPENSE_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Add Expense</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; background: #f5f7fb; color: #111827; }
      .card { background: white; padding: 1.2rem; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); max-width: 520px; }
      nav a { margin-right: 1rem; text-decoration: none; color: #2563eb; font-weight: bold; }
      form input, form select { display: block; margin-bottom: 0.7rem; padding: 0.6rem; width: 100%; max-width: 320px; }
      button { background: #2563eb; color: white; border: none; padding: 0.7rem 1rem; border-radius: 8px; cursor: pointer; }
    </style>
  </head>
  <body>
    <nav>
      <a href="/">Dashboard</a>
      <a href="/add">Add Expense</a>
      <a href="/recurring">Recurring</a>
      <a href="/export-csv">Export CSV</a>
      <a href="/logout">Logout</a>
    </nav>
    <div class="card">
      <h1>Add Expense</h1>
      <form method="post" action="/add">
        <label>Date</label>
        <input type="date" name="expense_date" required>
        <label>Description</label>
        <input type="text" name="description" placeholder="Coffee, rent, fuel" required>
        <label>Category</label>
        <select name="category" required>
          {% for category in categories %}
          <option value="{{ category }}">{{ category }}</option>
          {% endfor %}
        </select>
        <label>Subcategory</label>
        <select name="subcategory" required>
          {% for subcategory in subcategories %}
          <option value="{{ subcategory }}">{{ subcategory }}</option>
          {% endfor %}
        </select>
        <label>Price</label>
        <input type="number" step="0.01" name="price" required>
        <label>Spender</label>
        <input type="text" name="spender_username" value="{{ username }}" required>
        <button type="submit">Save Expense</button>
      </form>
      <p><a href="/">Back to dashboard</a></p>
    </div>
  </body>
</html>
"""

AUTH_TEMPLATE = """
<!doctype html>
<html>
  <head><meta charset="utf-8"><title>{{ title }}</title></head>
  <body>
    <h1>{{ title }}</h1>
    <form method="post">
      <input type="text" name="username" placeholder="Username" required>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit">{{ title }}</button>
    </form>
    {% if title == 'Login' %}<p><a href="/register">Create account</a></p>{% endif %}
  </body>
</html>
"""

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(user_id, name)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subcategories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(user_id, category_id, name),
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            expense_date TEXT NOT NULL,
            description TEXT NOT NULL,
            category_id INTEGER,
            subcategory_id INTEGER,
            price REAL NOT NULL,
            spender_username TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(category_id) REFERENCES categories(id),
            FOREIGN KEY(subcategory_id) REFERENCES subcategories(id)
        )
    ''')
    def has_column(table_name, column_name):
        table_exists = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
        if not table_exists:
            return False
        columns = [row[1] for row in conn.execute(f'PRAGMA table_info({table_name})').fetchall()]
        return column_name in columns

    if not has_column('users', 'password_hash'):
        conn.execute('ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ""')
    if not has_column('categories', 'user_id'):
        conn.execute('ALTER TABLE categories ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1')
    if not has_column('subcategories', 'user_id'):
        conn.execute('ALTER TABLE subcategories ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1')
    if not has_column('expenses', 'user_id'):
        conn.execute('ALTER TABLE expenses ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1')
    if not has_column('expenses', 'spender_username'):
        conn.execute("ALTER TABLE expenses ADD COLUMN spender_username TEXT NOT NULL DEFAULT ''")

    if conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
        conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', ('household', generate_password_hash('change-me')))

    conn.commit()
    conn.close()


def get_or_create_category(conn, user_id, name):
    trimmed = (name or '').strip()
    if not trimmed:
        return None
    existing = conn.execute('SELECT id FROM categories WHERE user_id = ? AND name = ?', (user_id, trimmed)).fetchone()
    if existing:
        return existing['id']
    cursor = conn.execute('INSERT INTO categories (user_id, name) VALUES (?, ?)', (user_id, trimmed))
    return cursor.lastrowid


def get_or_create_subcategory(conn, user_id, category_id, name):
    if not category_id:
        return None
    trimmed = (name or '').strip()
    if not trimmed:
        return None
    existing = conn.execute('SELECT id FROM subcategories WHERE user_id = ? AND category_id = ? AND name = ?', (user_id, category_id, trimmed)).fetchone()
    if existing:
        return existing['id']
    cursor = conn.execute('INSERT INTO subcategories (user_id, category_id, name) VALUES (?, ?, ?)', (user_id, category_id, trimmed))
    return cursor.lastrowid


@app.before_request
def before_request():
    init_db()
    if request.endpoint not in {'login', 'register'} and 'user_id' not in session:
        if request.path.startswith('/static'):
            return None
        if request.path != '/' and not request.path.startswith('/login') and not request.path.startswith('/register'):
            return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
    return render_template_string(AUTH_TEMPLATE, title='Login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        if conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            conn.close()
            return render_template_string(AUTH_TEMPLATE, title='Register')
        conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, generate_password_hash(password)))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template_string(AUTH_TEMPLATE, title='Register')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    expenses = conn.execute('''
        SELECT e.id, e.expense_date, e.description, e.price, c.name AS category_name, s.name AS subcategory_name, e.spender_username
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        LEFT JOIN subcategories s ON e.subcategory_id = s.id
        ORDER BY e.expense_date DESC, e.id DESC LIMIT 20
    ''').fetchall()
    total_spent = conn.execute('SELECT COALESCE(SUM(price), 0) FROM expenses').fetchone()[0]
    entry_count = conn.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]
    category_count = conn.execute('''
        SELECT COUNT(DISTINCT COALESCE(c.name, 'Uncategorized'))
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
    ''').fetchone()[0]
    monthly_totals = conn.execute('''
        SELECT strftime('%Y-%m', expense_date) AS month, SUM(price) AS total
        FROM expenses
        GROUP BY strftime('%Y-%m', expense_date)
        ORDER BY month DESC LIMIT 6
    ''').fetchall()
    category_totals = conn.execute('''
        SELECT COALESCE(c.name, 'Uncategorized') AS category, SUM(e.price) AS total
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        GROUP BY COALESCE(c.name, 'Uncategorized')
        ORDER BY total DESC
    ''').fetchall()
    conn.close()
    return render_template_string(
        HTML_TEMPLATE,
        expenses=expenses,
        total_spent=f'{total_spent:.2f}',
        entry_count=entry_count,
        category_count=category_count,
        monthly_totals=monthly_totals,
        category_totals=category_totals,
        username=session.get('username', 'User'),
    )


@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    if request.method == 'POST':
        date = request.form['expense_date']
        description = request.form['description']
        category_name = request.form['category']
        subcategory_name = request.form['subcategory']
        price = float(request.form['price'])
        spender = request.form.get('spender_username', '').strip() or session.get('username', 'User')
        conn = get_db_connection()
        category_id = get_or_create_category(conn, user_id, category_name)
        subcategory_id = get_or_create_subcategory(conn, user_id, category_id, subcategory_name)
        conn.execute(
            'INSERT INTO expenses (user_id, expense_date, description, category_id, subcategory_id, price, spender_username) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, date, description, category_id, subcategory_id, price, spender),
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    categories = ['Food', 'Transport', 'Housing', 'Utilities', 'Health', 'Entertainment', 'Shopping', 'Education', 'Travel', 'Personal', 'Salary', 'Other']
    subcategories = ['Groceries', 'Dining Out', 'Coffee', 'Fuel', 'Transit', 'Rent', 'Mortgage', 'Electricity', 'Water', 'Internet', 'Medicine', 'Insurance', 'Movies', 'Streaming', 'Clothes', 'Electronics', 'Books', 'Tuition', 'Flights', 'Hotels', 'Gifts', 'Beauty', 'Sports', 'Salary', 'Bonus', 'Other']
    return render_template_string(ADD_EXPENSE_TEMPLATE, username=session.get('username', 'User'), categories=categories, subcategories=subcategories)


@app.route('/edit-expense/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    expense = conn.execute('SELECT * FROM expenses WHERE id = ?', (expense_id,)).fetchone()
    if not expense:
        conn.close()
        return redirect(url_for('index'))
    if request.method == 'POST':
        date = request.form['expense_date']
        description = request.form['description']
        category_name = request.form['category']
        subcategory_name = request.form['subcategory']
        price = float(request.form['price'])
        spender = request.form.get('spender_username', '').strip() or session.get('username', 'User')
        category_id = get_or_create_category(conn, session['user_id'], category_name)
        subcategory_id = get_or_create_subcategory(conn, session['user_id'], category_id, subcategory_name)
        conn.execute(
            'UPDATE expenses SET expense_date=?, description=?, category_id=?, subcategory_id=?, price=?, spender_username=? WHERE id=?',
            (date, description, category_id, subcategory_id, price, spender, expense_id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    category_name = ''
    subcategory_name = ''
    if expense['category_id']:
        category_name = conn.execute('SELECT name FROM categories WHERE id = ?', (expense['category_id'],)).fetchone()['name']
    if expense['subcategory_id']:
        subcategory_name = conn.execute('SELECT name FROM subcategories WHERE id = ?', (expense['subcategory_id'],)).fetchone()['name']
    conn.close()
    return render_template_string("""
    <!doctype html><html><body>
      <h1>Edit Expense</h1>
      <form method="post">
        <input type="date" name="expense_date" value="{{ expense['expense_date'] }}" required>
        <input type="text" name="description" value="{{ expense['description'] }}" required>
        <input type="text" name="category" value="{{ category_name }}" required>
        <input type="text" name="subcategory" value="{{ subcategory_name }}" required>
        <input type="number" step="0.01" name="price" value="{{ expense['price'] }}" required>
        <input type="text" name="spender_username" value="{{ expense['spender_username'] or username }}" required>
        <button type="submit">Save</button>
      </form>
      <p><a href="/">Back to dashboard</a></p>
    </body></html>
    """, expense=expense, category_name=category_name, subcategory_name=subcategory_name, username=session.get('username', 'User'))


@app.route('/delete-expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


@app.route('/export-csv')
def export_csv():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    rows = conn.execute('SELECT expense_date, description, price FROM expenses WHERE user_id = ? ORDER BY expense_date', (user_id,)).fetchall()
    conn.close()
    csv_lines = ['date,description,amount']
    for row in rows:
        csv_lines.append(f"{row['expense_date']},{row['description']},{row['price']}")
    output = '\n'.join(csv_lines) + '\n'
    return Response(output, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=expenses.csv'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
