from flask import Blueprint, request, redirect, render_template, url_for, make_response
from datetime import datetime
from database import get_db

tracker_bp = Blueprint('tracker', __name__)

# 1x1 transparent GIF pixel
TRACKING_PIXEL = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
    b'\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
    b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
)


@tracker_bp.route('/track/open/<token>')
def track_open(token):
    """Record email open via tracking pixel."""
    conn = get_db()
    log = conn.execute(
        "SELECT * FROM email_logs WHERE tracking_token = ?", (token,)
    ).fetchone()

    if log and not log['opened_at']:
        conn.execute(
            "UPDATE email_logs SET opened_at = ? WHERE tracking_token = ?",
            (datetime.utcnow(), token)
        )
        conn.commit()
    conn.close()

    # Return transparent 1x1 GIF
    response = make_response(TRACKING_PIXEL)
    response.headers['Content-Type'] = 'image/gif'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return response


@tracker_bp.route('/track/click/<token>')
def track_click(token):
    """Record link click and redirect to phishing landing page."""
    conn = get_db()
    log = conn.execute(
        "SELECT * FROM email_logs WHERE tracking_token = ?", (token,)
    ).fetchone()

    if log:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        ua = request.headers.get('User-Agent', '')
        conn.execute(
            "INSERT INTO click_logs (campaign_id, tracking_token, clicked_at, ip_address, user_agent) "
            "VALUES (?, ?, ?, ?, ?)",
            (log['campaign_id'], token, datetime.utcnow(), ip, ua)
        )
        conn.commit()
    conn.close()

    return redirect(url_for('tracker.phishing_page', token=token))


@tracker_bp.route('/phish/<token>')
def phishing_page(token):
    """Display fake login landing page."""
    conn = get_db()
    log = conn.execute(
        "SELECT * FROM email_logs WHERE tracking_token = ?", (token,)
    ).fetchone()
    conn.close()

    recipient_email = log['recipient_email'] if log else ''
    return render_template('phishing_page.html', token=token, prefill_email=recipient_email)


@tracker_bp.route('/phish/submit', methods=['POST'])
def phish_submit():
    """Capture credentials and show awareness page."""
    token = request.form.get('token', '')
    email = request.form.get('email', '')
    password = request.form.get('password', '')

    conn = get_db()
    log = conn.execute(
        "SELECT * FROM email_logs WHERE tracking_token = ?", (token,)
    ).fetchone()

    if log:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        # Store a masked version of the password (never store plaintext in production)
        masked_pw = password[:2] + '*' * (len(password) - 2) if len(password) > 2 else '***'
        conn.execute(
            "INSERT INTO captured_credentials "
            "(campaign_id, tracking_token, email, password_captured, submitted_at, ip_address) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (log['campaign_id'], token, email, masked_pw, datetime.utcnow(), ip)
        )
        conn.commit()
    conn.close()

    return render_template('awareness.html')
