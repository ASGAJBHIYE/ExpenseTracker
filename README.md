# Self-hosted Expense Tracker

This project is a simple self-hosted web app for tracking expenses. It uses Flask and a local SQLite database, so you can run it without any paid backend service.

## Features
- Add expenses with date, description, category, subcategory, and price
- Store data locally in SQLite
- Dashboard with totals, entry count, category count, and recent expenses
- Login and shared household dashboard
- CSV export

## Run locally
1. Install Python 3.10+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   python app.py
   ```
4. Open http://localhost:5000

## Deploy to PythonAnywhere
1. Create a PythonAnywhere account.
2. Open the Web tab and create a new web app.
3. Choose Flask and the Python version you want.
4. In the Code section, set the WSGI file to use the provided wsgi.py entrypoint.
5. Upload this project files to your PythonAnywhere home directory.
6. Install requirements in the Bash console:
   ```bash
   pip install -r requirements.txt
   ```
7. Reload the web app.

## Test
```bash
python -m unittest discover -s tests -v
```
# ExpenseTracker
