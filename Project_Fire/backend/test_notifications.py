import os
import asyncio
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText

load_dotenv()

def test_email():
    print("🚀 Testing Email Dispatch...")
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    email_user = os.getenv('EMAIL_USER')
    email_password = os.getenv('EMAIL_PASSWORD')
    emergency_emails = os.getenv('EMERGENCY_EMAILS', email_user).split(',')
    
    if not email_user or not email_password:
        print("❌ Error: EMAIL_USER or EMAIL_PASSWORD not set in .env")
        return

    msg = MIMEText('🔥 This is a test alert from the Agniveer Wildfire Detection System.')
    msg['Subject'] = '🚀 Agniveer System Test Alert'
    msg['From'] = email_user
    msg['To'] = emergency_emails[0].strip()
    
    try:
        print(f"Connecting to {smtp_server}:{smtp_port} as {email_user}...")
        server = None
        # server.set_debuglevel(1) # Uncomment for verbose logs

        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.ehlo()
        try:
            server.starttls()
            server.ehlo()
            server.login(email_user, email_password)
        except Exception:
            # STARTTLS not supported or failed. If server uses SSL port, try SMTP_SSL,
            # otherwise fall back to plaintext send (useful for local debug servers).
            try:
                if smtp_port == 465:
                    server.close()
                    server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15)
                    server.ehlo()
                    server.login(email_user, email_password)
                else:
                    # Plain send without TLS (only for local/non-production testing)
                    pass
            except Exception:
                # ignore and proceed to send (may fail)
                pass

        server.send_message(msg)
        try:
            server.quit()
        except Exception:
            try:
                server.close()
            except Exception:
                pass

        print(f"✅ Email sent successfully to {msg['To']}.")
    except Exception as e:
        print(f"❌ Email failed: {e}")

if __name__ == "__main__":
    print("=" * 40)
    print("AGNIVEER NOTIFICATION TESTER")
    print("=" * 40)
    test_email()
    print("=" * 40)
