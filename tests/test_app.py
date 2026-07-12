import os
import sqlite3
import tempfile
import unittest

from app import app, init_db


class ExpenseTrackerAppTests(unittest.TestCase):
    def setUp(self):
        self.db_path = tempfile.NamedTemporaryFile(delete=False).name
        app.config['DATABASE'] = self.db_path
        init_db()
        self.client = app.test_client()
        self.client.testing = True

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_dashboard_requires_login(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)

    def test_expense_form_loads_after_login(self):
        self.client.post('/register', data={'username':'tester','password':'secret'}, follow_redirects=True)
        self.client.post('/login', data={'username':'tester','password':'secret'}, follow_redirects=True)
        response = self.client.get('/add')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Add Expense', response.data)
        self.assertIn(b'name="category"', response.data)
        self.assertIn(b'name="subcategory"', response.data)

    def test_expense_can_be_added(self):
        self.client.post('/register', data={'username':'tester','password':'secret'}, follow_redirects=True)
        self.client.post('/login', data={'username':'tester','password':'secret'}, follow_redirects=True)
        response = self.client.post('/add', data={
            'expense_date': '2026-07-12',
            'description': 'Dinner',
            'category': 'Food',
            'subcategory': 'Dining',
            'price': '24.50',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dinner', response.data)
        self.assertIn(b'Food', response.data)

    def test_csv_export_is_available(self):
        self.client.post('/register', data={'username':'tester','password':'secret'}, follow_redirects=True)
        self.client.post('/login', data={'username':'tester','password':'secret'}, follow_redirects=True)
        response = self.client.get('/export-csv')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'description', response.data)

    def test_shared_dashboard_is_visible_to_other_household_users(self):
        self.client.post('/register', data={'username':'tester','password':'secret'}, follow_redirects=True)
        self.client.post('/register', data={'username':'wife','password':'secret'}, follow_redirects=True)
        self.client.post('/login', data={'username':'tester','password':'secret'}, follow_redirects=True)
        self.client.post('/add', data={
            'expense_date': '2026-07-12',
            'description': 'Groceries',
            'category': 'Food',
            'subcategory': 'Household',
            'price': '55.00',
            'spender_username': 'tester'
        }, follow_redirects=True)

        self.client.post('/login', data={'username':'wife','password':'secret'}, follow_redirects=True)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Groceries', response.data)
        self.assertIn(b'tester', response.data)

    def test_expense_can_be_edited_and_deleted(self):
        self.client.post('/register', data={'username':'tester','password':'secret'}, follow_redirects=True)
        self.client.post('/login', data={'username':'tester','password':'secret'}, follow_redirects=True)
        self.client.post('/add', data={
            'expense_date': '2026-07-12',
            'description': 'Lunch',
            'category': 'Food',
            'subcategory': 'Lunch',
            'price': '10.00',
            'spender_username': 'tester'
        }, follow_redirects=True)
        conn = sqlite3.connect(self.db_path)
        expense_id = conn.execute('SELECT id FROM expenses LIMIT 1').fetchone()[0]
        conn.close()

        edit_response = self.client.post(f'/edit-expense/{expense_id}', data={
            'expense_date': '2026-07-13',
            'description': 'Updated Lunch',
            'category': 'Food',
            'subcategory': 'Lunch',
            'price': '12.50',
            'spender_username': 'tester'
        }, follow_redirects=True)
        self.assertEqual(edit_response.status_code, 200)
        self.assertIn(b'Updated Lunch', edit_response.data)

        delete_response = self.client.post(f'/delete-expense/{expense_id}', follow_redirects=True)
        self.assertEqual(delete_response.status_code, 200)
        self.assertNotIn(b'Updated Lunch', delete_response.data)


if __name__ == '__main__':
    unittest.main()
