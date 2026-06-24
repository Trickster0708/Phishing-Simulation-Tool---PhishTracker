import unittest
import os
import sqlite3
from app import app
from database import get_db, init_db, DB_PATH
from werkzeug.security import generate_password_hash

class TestPhishSimLaunch(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        self.original_db_path = DB_PATH
        self.test_db_path = os.path.join(os.path.dirname(__file__), 'phishsim_test_launch.db')
        
        import database
        database.DB_PATH = self.test_db_path
        
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        init_db()
        
        # Seed test admin account
        conn = get_db()
        conn.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            ('testadmin', generate_password_hash('testpassword123'))
        )
        # Seed a campaign
        conn.execute(
            "INSERT INTO campaigns (name, email_subject, email_template, target_emails, status) VALUES (?, ?, ?, ?, ?)",
            ('Test Campaign', 'Test Subject', 'Test template body', 'target1@example.com, target2@example.com', 'draft')
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass
        
        import database
        database.DB_PATH = self.original_db_path

    def login(self, username, password):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def test_launch_campaign_flow(self):
        """Test launching the seeded campaign."""
        # Log in first
        self.login('testadmin', 'testpassword123')
        
        # Launch campaign 1
        response = self.client.post('/campaigns/1/launch', follow_redirects=True)
        print("Response status:", response.status_code)
        print("Response data snippet:", response.data[:1000].decode('utf-8', errors='ignore').encode('ascii', errors='backslashreplace').decode('ascii'))
        
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
