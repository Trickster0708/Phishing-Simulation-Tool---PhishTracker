import sqlite3
import os
import shutil

# Vercel and other serverless environments have a read-only filesystem, except for /tmp.
# We dynamically detect if the current directory is read-only or if we are running under Vercel,
# and route the DB path to /tmp/phishsim.db if needed.
_base_dir = os.path.dirname(__file__)
if os.environ.get('VERCEL') == '1' or not os.access(_base_dir, os.W_OK):
    DB_PATH = '/tmp/phishsim.db'
    # Copy the packaged DB from the repo to /tmp on startup so seed data / accounts aren't lost
    repo_db = os.path.join(_base_dir, 'phishsim.db')
    if os.path.exists(repo_db) and not os.path.exists(DB_PATH):
        try:
            shutil.copy(repo_db, DB_PATH)
        except Exception as e:
            print(f"[-] Failed to copy DB to /tmp: {e}")
else:
    DB_PATH = os.path.join(_base_dir, 'phishsim.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email_subject TEXT NOT NULL,
            email_template TEXT NOT NULL,
            target_emails TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            launched_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            recipient_email TEXT NOT NULL,
            tracking_token TEXT UNIQUE NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            opened_at TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        );

        CREATE TABLE IF NOT EXISTS click_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            tracking_token TEXT NOT NULL,
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        );

        CREATE TABLE IF NOT EXISTS captured_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            tracking_token TEXT NOT NULL,
            email TEXT NOT NULL,
            password_captured TEXT NOT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        );
    """)

    conn.commit()
    conn.close()
    print("[+] Database initialized successfully.")
