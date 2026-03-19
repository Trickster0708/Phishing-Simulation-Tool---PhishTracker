import smtplib
import os
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from database import get_db
from dotenv import load_dotenv

load_dotenv()

MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.mailtrap.io')
MAIL_PORT = int(os.getenv('MAIL_PORT', 2525))
MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
MAIL_FROM = os.getenv('MAIL_FROM', 'phishsim@example.com')


def send_campaign_emails(campaign, base_url):
    """
    Send phishing simulation emails for a campaign.
    Returns (success_count, fail_count, errors).
    """
    target_emails = [e.strip() for e in campaign['target_emails'].split(',') if e.strip()]
    success_count = 0
    fail_count = 0
    errors = []

    try:
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        server.starttls()
        if MAIL_USERNAME and MAIL_PASSWORD:
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
    except Exception as e:
        return 0, len(target_emails), [f"SMTP connection failed: {str(e)}"]

    for email in target_emails:
        token = str(uuid.uuid4())

        # Build tracking URLs
        track_open_url = f"{base_url}/track/open/{token}"
        track_click_url = f"{base_url}/track/click/{token}"

        # Build email HTML
        html_body = build_email_html(
            campaign['email_template'],
            track_click_url,
            track_open_url
        )

        msg = MIMEMultipart('alternative')
        msg['Subject'] = campaign['email_subject']
        msg['From'] = MAIL_FROM
        msg['To'] = email
        msg.attach(MIMEText(html_body, 'html'))

        try:
            server.sendmail(MAIL_FROM, email, msg.as_string())

            # Log to DB
            conn = get_db()
            conn.execute(
                "INSERT INTO email_logs (campaign_id, recipient_email, tracking_token) VALUES (?, ?, ?)",
                (campaign['id'], email, token)
            )
            conn.commit()
            conn.close()
            success_count += 1
        except Exception as e:
            fail_count += 1
            errors.append(f"Failed to send to {email}: {str(e)}")

    try:
        server.quit()
    except Exception:
        pass

    return success_count, fail_count, errors


def build_email_html(template_body, click_url, open_pixel_url):
    """Wrap the template body with tracking pixel and CTA button."""
    tracking_pixel = f'<img src="{open_pixel_url}" width="1" height="1" style="display:none" alt="" />'
    cta_button = f'''
    <div style="text-align:center; margin: 30px 0;">
        <a href="{click_url}" 
           style="background:#0052cc; color:white; padding:14px 28px;
                  text-decoration:none; border-radius:5px; font-size:16px;
                  font-weight:bold; display:inline-block;">
            Click Here to Verify Your Account
        </a>
    </div>'''

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background:#f4f4f4; padding:20px; border-radius:8px;">
            {template_body}
            {cta_button}
            <p style="color:#999; font-size:12px; text-align:center;">
                &copy; 2026 Security Department
            </p>
        </div>
        {tracking_pixel}
    </body>
    </html>
    """
