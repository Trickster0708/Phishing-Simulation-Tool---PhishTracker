import unittest
import os
import sqlite3
from app import app
from database import get_db, init_db, DB_PATH
from werkzeug.security import generate_password_hash

class TestPhishSimWorkflow(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        # Save active DB state and use a temporary database for testing
        self.original_db_path = DB_PATH
        self.test_db_path = os.path.join(os.path.dirname(__file__), 'phishsim_test.db')
        
        # Override DB_PATH in database module to point to the test db
        import database
        database.DB_PATH = self.test_db_path
        
        # Re-initialize the database for the test run
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        init_db()
        
        # Seed test admin account
        conn = get_db()
        conn.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            ('testadmin', generate_password_hash('testpassword123'))
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        # Clean up test database
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass
        
        # Restore original DB_PATH
        import database
        database.DB_PATH = self.original_db_path

    def login(self, username, password):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def test_database_initialization(self):
        """Test if the database was initialized with the correct tables."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        self.assertIn('admins', tables)
        self.assertIn('campaigns', tables)
        self.assertIn('email_logs', tables)
        self.assertIn('click_logs', tables)
        self.assertIn('captured_credentials', tables)

    def test_admin_login(self):
        """Test admin login validation."""
        # Test invalid credentials
        response = self.login('wronguser', 'wrongpass')
        self.assertIn(b'Invalid username or password', response.data)
        
        # Test valid credentials
        response = self.login('testadmin', 'testpassword123')
        self.assertIn('Change Password', response.data.decode('utf-8', errors='ignore'))

    def test_username_change_flow(self):
        """Test username update with various validation cases."""
        # Log in first
        self.login('testadmin', 'testpassword123')
        
        # 1. Test changing to a username that is too short
        response = self.client.post('/change-password', data={
            'action': 'username',
            'new_username': 'ab',
            'current_password': 'testpassword123'
        }, follow_redirects=True)
        self.assertIn(b'Username must be at least 3 characters', response.data)
        
        # 2. Test changing with an incorrect current password
        response = self.client.post('/change-password', data={
            'action': 'username',
            'new_username': 'validuser',
            'current_password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertIn(b'Current password is incorrect', response.data)

        # 3. Test changing to an already taken username
        # Create another admin in database first
        conn = get_db()
        conn.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            ('anotheradmin', generate_password_hash('somepass123'))
        )
        conn.commit()
        conn.close()
        
        response = self.client.post('/change-password', data={
            'action': 'username',
            'new_username': 'anotheradmin',
            'current_password': 'testpassword123'
        }, follow_redirects=True)
        self.assertIn(b'That username is already taken', response.data)

        # 4. Test successful username update
        response = self.client.post('/change-password', data={
            'action': 'username',
            'new_username': 'newadminname',
            'current_password': 'testpassword123'
        }, follow_redirects=True)
        
        # Verify redirect to dashboard/settings updated successfully
        self.assertIn('Username changed to &#34;newadminname&#34;', response.data.decode('utf-8', errors='ignore'))
        
        # Verify db contains the updated username
        conn = get_db()
        row = conn.execute("SELECT username FROM admins WHERE id=1").fetchone()
        conn.close()
        self.assertEqual(row['username'], 'newadminname')

if __name__ == '__main__':
    unittest.main()
