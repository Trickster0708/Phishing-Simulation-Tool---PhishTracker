import os
import sys
import click
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime

from database import get_db, init_db
from tracker import tracker_bp
from email_sender import send_campaign_emails

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-please-change')

# ── Login Manager ──────────────────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access the admin panel.'
login_manager.login_message_category = 'warning'


class Admin(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM admins WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        return Admin(row['id'], row['username'])
    return None


# ── Register Blueprints ────────────────────────────────────────────────────────
app.register_blueprint(tracker_bp)


# ── Auth Routes ────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        row = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
        conn.close()
        if row and check_password_hash(row['password_hash'], password):
            admin = Admin(row['id'], row['username'])
            login_user(admin)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ── Dashboard / Analytics ──────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    total_campaigns = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    total_sent = conn.execute("SELECT COUNT(*) FROM email_logs").fetchone()[0]
    total_opened = conn.execute("SELECT COUNT(*) FROM email_logs WHERE opened_at IS NOT NULL").fetchone()[0]
    total_clicked = conn.execute("SELECT COUNT(*) FROM click_logs").fetchone()[0]
    total_creds = conn.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]

    # Per-campaign stats for chart
    campaigns = conn.execute("SELECT id, name FROM campaigns ORDER BY created_at DESC").fetchall()
    chart_labels = []
    chart_sent = []
    chart_clicked = []
    chart_creds = []
    for c in campaigns:
        chart_labels.append(c['name'])
        sent = conn.execute("SELECT COUNT(*) FROM email_logs WHERE campaign_id=?", (c['id'],)).fetchone()[0]
        clicked = conn.execute("SELECT COUNT(*) FROM click_logs WHERE campaign_id=?", (c['id'],)).fetchone()[0]
        creds = conn.execute("SELECT COUNT(*) FROM captured_credentials WHERE campaign_id=?", (c['id'],)).fetchone()[0]
        chart_sent.append(sent)
        chart_clicked.append(clicked)
        chart_creds.append(creds)

    conn.close()

    click_rate = round((total_clicked / total_sent * 100), 1) if total_sent > 0 else 0
    cred_rate = round((total_creds / total_sent * 100), 1) if total_sent > 0 else 0
    open_rate = round((total_opened / total_sent * 100), 1) if total_sent > 0 else 0

    return render_template('dashboard.html',
        total_campaigns=total_campaigns,
        total_sent=total_sent,
        total_opened=total_opened,
        total_clicked=total_clicked,
        total_creds=total_creds,
        click_rate=click_rate,
        cred_rate=cred_rate,
        open_rate=open_rate,
        chart_labels=chart_labels,
        chart_sent=chart_sent,
        chart_clicked=chart_clicked,
        chart_creds=chart_creds
    )


# ── Campaigns ──────────────────────────────────────────────────────────────────
@app.route('/campaigns')
@login_required
def campaigns():
    conn = get_db()
    rows = conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC").fetchall()
    campaign_stats = []
    for row in rows:
        sent = conn.execute("SELECT COUNT(*) FROM email_logs WHERE campaign_id=?", (row['id'],)).fetchone()[0]
        clicked = conn.execute("SELECT COUNT(*) FROM click_logs WHERE campaign_id=?", (row['id'],)).fetchone()[0]
        creds = conn.execute("SELECT COUNT(*) FROM captured_credentials WHERE campaign_id=?", (row['id'],)).fetchone()[0]
        campaign_stats.append({**dict(row), 'sent': sent, 'clicked': clicked, 'creds': creds})
    conn.close()
    return render_template('campaigns.html', campaigns=campaign_stats)


@app.route('/campaigns/new', methods=['GET', 'POST'])
@login_required
def new_campaign():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        subject = request.form.get('subject', '').strip()
        template = request.form.get('template', '').strip()
        targets = request.form.get('targets', '').strip()

        if not all([name, subject, template, targets]):
            flash('All fields are required.', 'danger')
            return render_template('new_campaign.html')

        conn = get_db()
        conn.execute(
            "INSERT INTO campaigns (name, email_subject, email_template, target_emails, status) VALUES (?,?,?,?,?)",
            (name, subject, template, targets, 'draft')
        )
        conn.commit()
        conn.close()
        flash(f'Campaign "{name}" created successfully!', 'success')
        return redirect(url_for('campaigns'))

    return render_template('new_campaign.html')


@app.route('/campaigns/<int:campaign_id>')
@login_required
def campaign_detail(campaign_id):
    conn = get_db()
    campaign = conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    if not campaign:
        conn.close()
        flash('Campaign not found.', 'danger')
        return redirect(url_for('campaigns'))

    email_logs = conn.execute(
        "SELECT * FROM email_logs WHERE campaign_id=? ORDER BY sent_at DESC",
        (campaign_id,)
    ).fetchall()

    detail_rows = []
    for log in email_logs:
        clicked = conn.execute(
            "SELECT * FROM click_logs WHERE tracking_token=? LIMIT 1",
            (log['tracking_token'],)
        ).fetchone()
        cred = conn.execute(
            "SELECT * FROM captured_credentials WHERE tracking_token=? LIMIT 1",
            (log['tracking_token'],)
        ).fetchone()
        detail_rows.append({
            'email': log['recipient_email'],
            'sent': log['sent_at'],
            'opened': log['opened_at'],
            'clicked': clicked['clicked_at'] if clicked else None,
            'cred_submitted': cred['submitted_at'] if cred else None,
        })

    conn.close()
    return render_template('campaign_detail.html', campaign=campaign, rows=detail_rows)


@app.route('/campaigns/<int:campaign_id>/launch', methods=['POST'])
@login_required
def launch_campaign(campaign_id):
    conn = get_db()
    campaign = conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    if not campaign:
        conn.close()
        flash('Campaign not found.', 'danger')
        return redirect(url_for('campaigns'))

    base_url = request.host_url.rstrip('/')
    success, fail, errors = send_campaign_emails(dict(campaign), base_url)

    conn.execute(
        "UPDATE campaigns SET status='launched', launched_at=? WHERE id=?",
        (datetime.utcnow(), campaign_id)
    )
    conn.commit()
    conn.close()

    flash(f'Campaign launched! ✅ {success} emails sent, ❌ {fail} failed.', 'success' if success else 'danger')
    return redirect(url_for('campaign_detail', campaign_id=campaign_id))


@app.route('/campaigns/<int:campaign_id>/delete', methods=['POST'])
@login_required
def delete_campaign(campaign_id):
    conn = get_db()
    conn.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
    conn.execute("DELETE FROM email_logs WHERE campaign_id=?", (campaign_id,))
    conn.execute("DELETE FROM click_logs WHERE campaign_id=?", (campaign_id,))
    conn.execute("DELETE FROM captured_credentials WHERE campaign_id=?", (campaign_id,))
    conn.commit()
    conn.close()
    flash('Campaign deleted.', 'info')
    return redirect(url_for('campaigns'))


# ── CLI Commands ───────────────────────────────────────────────────────────────
@app.cli.command('init-db')
def init_db_command():
    """Initialize the database."""
    init_db()
    click.echo('Database initialized.')


@app.cli.command('create-admin')
@click.option('--username', prompt='Admin username', help='Admin username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
def create_admin(username, password):
    """Create an admin user."""
    conn = get_db()
    existing = conn.execute("SELECT id FROM admins WHERE username=?", (username,)).fetchone()
    if existing:
        click.echo(f'Admin "{username}" already exists.')
        conn.close()
        return
    hashed = generate_password_hash(password)
    conn.execute("INSERT INTO admins (username, password_hash) VALUES (?,?)", (username, hashed))
    conn.commit()
    conn.close()
    click.echo(f'Admin "{username}" created successfully.')


if __name__ == '__main__':
    if not os.path.exists('phishsim.db'):
        init_db()
        # Create default admin on first run
        conn = get_db()
        exists = conn.execute("SELECT id FROM admins WHERE username='admin'").fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO admins (username, password_hash) VALUES (?,?)",
                ('admin', generate_password_hash('admin123'))
            )
            conn.commit()
            print("[+] Default admin created: admin / admin123  (change this immediately!)")
        conn.close()

    app.run(debug=True, host='0.0.0.0', port=5000)
