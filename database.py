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


class DictRow(dict):
    """Subclass of dict to support both row['column'] and row[index] lookup patterns."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class CursorWrapper:
    def __init__(self, cursor, is_pg=False):
        self.cursor = cursor
        self.is_pg = is_pg

    def fetchone(self):
        try:
            row = self.cursor.fetchone()
        except Exception:
            return None
        if row is None:
            return None
        return DictRow(row) if self.is_pg else row

    def fetchall(self):
        try:
            rows = self.cursor.fetchall()
        except Exception:
            return []
        return [DictRow(r) for r in rows] if self.is_pg else rows


class DbConnection:
    def __init__(self, conn, is_pg=False):
        self.conn = conn
        self.is_pg = is_pg

    def cursor(self):
        return self.conn.cursor()

    @property
    def row_factory(self):
        return self.conn.row_factory

    @row_factory.setter
    def row_factory(self, val):
        self.conn.row_factory = val

    def executescript(self, sql):
        if self.is_pg:
            cur = self.conn.cursor()
            cur.execute(sql)
        else:
            self.conn.executescript(sql)

    def execute(self, sql, params=()):
        if self.is_pg:
            # PostgreSQL uses %s instead of ? for query placeholders
            sql = sql.replace('?', '%s')
            cur = self.conn.cursor()
            cur.execute(sql, params)
            return CursorWrapper(cur, is_pg=True)
        else:
            return self.conn.execute(sql, params)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


def get_db():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        # Use RealDictCursor to fetch rows as dictionaries for easy conversion
        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        return DbConnection(conn, is_pg=True)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return DbConnection(conn, is_pg=False)


def init_db():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        import psycopg2
        conn = psycopg2.connect(db_url)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS campaigns (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email_subject VARCHAR(255) NOT NULL,
                email_template TEXT NOT NULL,
                target_emails TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                launched_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS email_logs (
                id SERIAL PRIMARY KEY,
                campaign_id INTEGER NOT NULL,
                recipient_email VARCHAR(255) NOT NULL,
                tracking_token VARCHAR(255) UNIQUE NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                opened_at TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS click_logs (
                id SERIAL PRIMARY KEY,
                campaign_id INTEGER NOT NULL,
                tracking_token VARCHAR(255) NOT NULL,
                clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent TEXT,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS captured_credentials (
                id SERIAL PRIMARY KEY,
                campaign_id INTEGER NOT NULL,
                tracking_token VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                password_captured VARCHAR(255) NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        conn.close()
        print("[+] PostgreSQL Database initialized successfully.")
    else:
        conn = get_db()
        conn.conn.executescript("""
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
        print("[+] SQLite Database initialized successfully.")
