import asyncio
import logging
import time
from typing import List, Dict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from firebase_admin import messaging
from datetime import datetime

load_dotenv()

# Module logger
logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        # Email settings
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.smtp_debug = os.getenv('SMTP_DEBUG', 'False').lower() == 'true'
        self.smtp_max_retries = int(os.getenv('SMTP_MAX_RETRIES', '3'))
    
    async def send_alerts(self, detection: Dict, nearby_stations: List[Dict]):
        """Send alerts through multiple channels (Email and Push)"""
        tasks = []
        
        # Send emails to emergency contacts and admin
        _emails = os.getenv('EMERGENCY_EMAILS')
        if _emails and _emails.strip():
            emergency_emails = [e.strip() for e in _emails.split(',') if e.strip()]
        elif self.email_user:
            emergency_emails = [self.email_user]
        else:
            emergency_emails = []

        for email in emergency_emails:
            tasks.append(self.send_email(email, detection))
        
        # Send push notifications
        tasks.append(self.send_push_notification(detection))
        
        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Notification {i} failed: {result}")
    
    async def send_email(self, to: str, detection: Dict):
        """Send email alert with HTML formatting"""
        if not self.email_user or not self.email_password:
            logger.error("Skipping email to %s: EMAIL_USER or EMAIL_PASSWORD not configured", to)
            return False

        # Build message
        msg = MIMEMultipart('alternative')
        msg['From'] = self.email_user
        msg['To'] = to
        msg['Subject'] = f"🚨 WILDFIRE ALERT - {detection['severity'].upper()}"

        # Create both plain text and HTML versions
        text_body = self._format_text_email(detection)
        html_body = self._format_html_email(detection)

        # Attach parts
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        # Perform blocking SMTP send in a thread to avoid blocking the event loop
        try:
            result = await asyncio.to_thread(self._send_email_sync, msg)
            if result:
                logger.info("Email sent to %s", to)
            else:
                logger.error("Email failed to %s", to)
            return result
        except Exception as e:
            logger.exception("Email failed to %s: %s", to, e)
            return False

    def _send_email_sync(self, msg: MIMEMultipart) -> bool:
        """Blocking SMTP send with STARTTLS and SSL fallback."""
        # Retry loop for transient errors
        last_exc = None
        for attempt in range(1, max(1, self.smtp_max_retries) + 1):
            try:
                # Try plain SMTP with STARTTLS first
                try:
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15)
                    server.ehlo()
                    if self.smtp_debug:
                        server.set_debuglevel(1)
                    server.starttls()
                    server.ehlo()
                    server.login(self.email_user, self.email_password)
                except Exception:
                    # Fallback to SMTP_SSL (some providers require SSL on connect)
                    server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=15)
                    if self.smtp_debug:
                        server.set_debuglevel(1)
                    server.ehlo()
                    server.login(self.email_user, self.email_password)

                server.send_message(msg)
                try:
                    server.quit()
                except Exception:
                    server.close()
                return True

            except Exception as e:
                last_exc = e
                logger.warning("SMTP attempt %d failed: %s", attempt, e)
                # Exponential backoff before retrying
                if attempt < self.smtp_max_retries:
                    time.sleep(2 ** attempt)

        logger.error("All SMTP attempts failed: %s", last_exc)
        return False
    
    async def send_push_notification(self, detection: Dict):
        """Send push notification via FCM HTTP v1 using Firebase Admin SDK"""
        try:
            # Determine notification priority based on severity
            priority = 'high' if detection['severity'] in ['critical', 'high'] else 'normal'
            
            # Create message for the topic
            message = messaging.Message(
                topic='wildfire_alerts',
                notification=messaging.Notification(
                    title='🔥 Wildfire Detected',
                    body=f"{detection['severity'].upper()} severity at {detection.get('address', 'unknown location')}",
                ),
                data={
                    'detection_id': detection['id'],
                    'latitude': str(detection['latitude']),
                    'longitude': str(detection['longitude']),
                    'severity': detection['severity'],
                    'confidence': str(detection['confidence']),
                    'image_url': str(detection.get('image_url') or ''),
                    'timestamp': detection['timestamp'].isoformat() if isinstance(detection['timestamp'], datetime) else str(detection['timestamp']),
                    'click_action': 'OPEN_DETECTION'
                },
                android=messaging.AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        channel_id='wildfire_alerts',
                        sound='default',
                        icon='ic_notification',
                        color=self._get_severity_color(detection['severity'])
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1,
                        ),
                    ),
                ),
            )

            # Send the message
            response = messaging.send(message)
            print(f"✅ Push notification sent successfully: {response}")
            return True
            
        except Exception as e:
            print(f"❌ Push notification error: {e}")
            return False
            
    async def send_verified_alert(self, detection: Dict):
        """Send additional alerts when fire is verified"""
        try:
            emergency_emails = os.getenv('EMERGENCY_EMAILS', self.email_user).split(',')
            for email in emergency_emails:
                if email.strip():
                    await self.send_email(email.strip(), {**detection, '_verified': True})
            
            # Broadcast to all users
            await self.send_push_notification({
                **detection,
                'title': '🚨 VERIFIED WILDFIRE ALERT'
            })
            
        except Exception as e:
            print(f"Error sending verified alert: {e}")
    

    
    def _format_text_email(self, detection: Dict) -> str:
        """Format plain text email"""
        image_str = f"Detection Image: {detection['image_url']}" if detection.get('image_url') else "Detection Image: Not available"
        lines = [
            "WILDFIRE DETECTION ALERT",
            "=" * 40,
            "",
            f"Severity: {detection['severity'].upper()}",
            f"Confidence: {detection['confidence']*100:.0f}%",
            f"Time: {detection['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(detection['timestamp'], datetime) else str(detection['timestamp'])}",
            "",
            "LOCATION DETAILS:",
            f"Address: {detection.get('address', 'Unknown')}",
            f"City: {detection.get('city', 'Unknown')}",
            f"State: {detection.get('state', 'Unknown')}",
            f"Country: {detection.get('country', 'Unknown')}",
            f"Coordinates: {detection['latitude']}, {detection['longitude']}",
            "",
            "LINKS:",
            f"Google Maps: https://maps.google.com/?q={detection['latitude']},{detection['longitude']}",
            image_str,
            "",
            "=" * 40,
            "This is an automated alert from the Wildfire Detection System"
        ]
        
        return "\n".join(lines)
    
    def _format_html_email(self, detection: Dict) -> str:
        """Format HTML email"""
        severity_colors = {
            'critical': '#8b0000',
            'high': '#dc3545',
            'medium': '#ffc107',
            'low': '#28a745'
        }
        
        severity_color = severity_colors.get(detection['severity'], '#000000')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {severity_color}; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border-radius: 0 0 5px 5px; }}
                .severity-badge {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; text-transform: uppercase; }}
                .detail-row {{ margin: 10px 0; padding: 10px; background-color: white; border-radius: 3px; }}
                .label {{ font-weight: bold; color: #666; }}
                .value {{ color: #333; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: {severity_color}; color: white; text-decoration: none; border-radius: 3px; margin: 5px; }}
                .footer {{ margin-top: 20px; text-align: center; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 WILDFIRE ALERT</h1>
                    <div class="severity-badge">Severity: {detection['severity'].upper()}</div>
                </div>
                
                <div class="content">
                    <div class="detail-row">
                        <div class="label">📍 Location</div>
                        <div class="value">{detection.get('address', 'Unknown')}</div>
                        <div class="value">{detection.get('city', '')}, {detection.get('state', '')}</div>
                        <div class="value">{detection.get('country', '')}</div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">📊 Detection Details</div>
                        <div class="value">Confidence: {detection['confidence']*100:.1f}%</div>
                        <div class="value">Time: {detection['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(detection['timestamp'], datetime) else str(detection['timestamp'])}</div>
                        <div class="value">Status: {detection.get('status', 'pending').upper()}</div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">🌍 Coordinates</div>
                        <div class="value">Latitude: {detection['latitude']}</div>
                        <div class="value">Longitude: {detection['longitude']}</div>
                    </div>
                    
                    <div style="text-align: center; margin: 20px 0;">
                        <a href="https://maps.google.com/?q={detection['latitude']},{detection['longitude']}" class="button">📍 View on Map</a>
                        {f'<a href="{detection["image_url"]}" class="button">🖼️ View Image</a>' if detection.get("image_url") else ""}
                    </div>
                    
                    {f'<div style="text-align: center;"><img src="{detection["image_url"]}" alt="Fire detection" style="max-width: 100%; border-radius: 5px;"></div>' if detection.get("image_url") else '<div style="text-align: center; color: #666; font-style: italic;">No image available for this report</div>'}
                </div>
                
                <div class="footer">
                    <p>This is an automated alert from the Wildfire Detection System</p>
                    <p>© 2024 Wildfire Detection System. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_severity_color(self, severity: str) -> str:
        colors = {
            'critical': '#FF0000',
            'high': '#FF4444',
            'medium': '#FFAA00',
            'low': '#00FF00'
        }
        return colors.get(severity, '#000000')