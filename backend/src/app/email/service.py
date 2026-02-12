"""Email service for Scripe using SendGrid."""

from typing import Optional
import httpx

from app.logging_config import get_logger
from app.settings import settings

logger = get_logger(__name__)


class EmailService:
    """Email service using SendGrid API.

    Handles transactional emails:
    - Email verification
    - Password reset
    - Welcome emails
    """

    SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"

    def __init__(self):
        """Initialize email service."""
        self.api_key = settings.sendgrid_api_key
        self.from_email = settings.sendgrid_from_email
        self.from_name = settings.sendgrid_from_name
        self.enabled = bool(self.api_key)

        if not self.enabled:
            logger.warning("email_service_disabled", reason="SENDGRID_API_KEY not set")

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send an email via SendGrid API.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body
            text_content: Plain text body (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("email_not_sent", reason="service_disabled", to=to_email)
            return False

        payload = {
            "personalizations": [
                {
                    "to": [{"email": to_email}],
                    "subject": subject,
                }
            ],
            "from": {
                "email": self.from_email,
                "name": self.from_name,
            },
            "content": [
                {"type": "text/html", "value": html_content},
            ],
        }

        if text_content:
            payload["content"].insert(0, {"type": "text/plain", "value": text_content})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.SENDGRID_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )

                if response.status_code in (200, 201, 202):
                    logger.info("email_sent", to=to_email, subject=subject)
                    return True
                else:
                    logger.error(
                        "email_send_failed",
                        to=to_email,
                        status=response.status_code,
                        body=response.text[:200],
                    )
                    return False

        except httpx.RequestError as e:
            logger.error("email_send_error", to=to_email, error=str(e))
            return False

    async def send_verification_email(
        self,
        to_email: str,
        user_name: Optional[str],
        verification_token: str,
    ) -> bool:
        """Send email verification link.

        Args:
            to_email: User's email address
            user_name: User's name (optional)
            verification_token: JWT verification token

        Returns:
            True if sent successfully
        """
        base_url = settings.frontend_url or settings.allowed_origins.split(",")[0]
        verification_url = f"{base_url}/verify-email?token={verification_token}"

        subject = "Verifiziere deine E-Mail-Adresse - Scripe"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
                .button {{ display: inline-block; background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">Scripe</div>
                </div>

                <p>Hallo{' ' + user_name if user_name else ''},</p>

                <p>Vielen Dank für deine Registrierung bei Scripe! Bitte bestätige deine E-Mail-Adresse, indem du auf den folgenden Button klickst:</p>

                <p style="text-align: center;">
                    <a href="{verification_url}" class="button">E-Mail bestätigen</a>
                </p>

                <p>Oder kopiere diesen Link in deinen Browser:</p>
                <p style="word-break: break-all; color: #666;">{verification_url}</p>

                <p>Dieser Link ist 24 Stunden gültig.</p>

                <p>Falls du diese E-Mail nicht angefordert hast, kannst du sie ignorieren.</p>

                <div class="footer">
                    <p>&copy; 2024 Scripe - B2B Lead Generation</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
Hallo{' ' + user_name if user_name else ''},

Vielen Dank für deine Registrierung bei Scripe!

Bitte bestätige deine E-Mail-Adresse mit diesem Link:
{verification_url}

Dieser Link ist 24 Stunden gültig.

Falls du diese E-Mail nicht angefordert hast, kannst du sie ignorieren.

---
Scripe - B2B Lead Generation
        """

        return await self._send_email(to_email, subject, html_content, text_content)

    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: Optional[str],
        reset_token: str,
    ) -> bool:
        """Send password reset link.

        Args:
            to_email: User's email address
            user_name: User's name (optional)
            reset_token: JWT reset token

        Returns:
            True if sent successfully
        """
        base_url = settings.frontend_url or settings.allowed_origins.split(",")[0]
        reset_url = f"{base_url}/reset-password?token={reset_token}"

        subject = "Passwort zurücksetzen - Scripe"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
                .button {{ display: inline-block; background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .warning {{ background-color: #fef3c7; border: 1px solid #f59e0b; padding: 12px; border-radius: 6px; margin: 20px 0; }}
                .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">Scripe</div>
                </div>

                <p>Hallo{' ' + user_name if user_name else ''},</p>

                <p>Du hast eine Anfrage zum Zurücksetzen deines Passworts gestellt. Klicke auf den folgenden Button, um ein neues Passwort zu setzen:</p>

                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">Passwort zurücksetzen</a>
                </p>

                <p>Oder kopiere diesen Link in deinen Browser:</p>
                <p style="word-break: break-all; color: #666;">{reset_url}</p>

                <div class="warning">
                    <strong>Wichtig:</strong> Dieser Link ist nur 1 Stunde gültig.
                </div>

                <p>Falls du diese Anfrage nicht gestellt hast, ignoriere diese E-Mail. Dein Passwort bleibt unverändert.</p>

                <div class="footer">
                    <p>&copy; 2024 Scripe - B2B Lead Generation</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
Hallo{' ' + user_name if user_name else ''},

Du hast eine Anfrage zum Zurücksetzen deines Passworts gestellt.

Klicke auf diesen Link, um ein neues Passwort zu setzen:
{reset_url}

WICHTIG: Dieser Link ist nur 1 Stunde gültig.

Falls du diese Anfrage nicht gestellt hast, ignoriere diese E-Mail.
Dein Passwort bleibt unverändert.

---
Scripe - B2B Lead Generation
        """

        return await self._send_email(to_email, subject, html_content, text_content)

    async def send_welcome_email(
        self,
        to_email: str,
        user_name: Optional[str],
    ) -> bool:
        """Send welcome email after registration.

        Args:
            to_email: User's email address
            user_name: User's name (optional)

        Returns:
            True if sent successfully
        """
        base_url = settings.frontend_url or settings.allowed_origins.split(",")[0]

        subject = "Willkommen bei Scripe!"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
                .button {{ display: inline-block; background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .feature {{ padding: 15px; background-color: #f3f4f6; border-radius: 8px; margin: 10px 0; }}
                .feature-title {{ font-weight: bold; color: #2563eb; }}
                .credits-box {{ background-color: #dcfce7; border: 1px solid #22c55e; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0; }}
                .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">Scripe</div>
                </div>

                <p>Hallo{' ' + user_name if user_name else ''},</p>

                <p>Willkommen bei Scripe - deiner Plattform für B2B Lead Generation!</p>

                <div class="credits-box">
                    <strong>🎁 Dein Willkommensgeschenk:</strong><br>
                    <span style="font-size: 24px; color: #22c55e;">10 Credits</span><br>
                    <small>für deine ersten Recherchen</small>
                </div>

                <h3>Was du mit Scripe machen kannst:</h3>

                <div class="feature">
                    <div class="feature-title">🔍 Intelligente Suche</div>
                    <p>Finde Unternehmen nach Branche, Standort und Größe - mit KI-unterstützter Suche.</p>
                </div>

                <div class="feature">
                    <div class="feature-title">📞 Verifizierte Kontaktdaten</div>
                    <p>Erhalte validierte Telefonnummern, E-Mails und Websites für jeden Lead.</p>
                </div>

                <div class="feature">
                    <div class="feature-title">📊 Qualitäts-Scoring</div>
                    <p>Jeder Lead wird automatisch nach Datenqualität bewertet.</p>
                </div>

                <p style="text-align: center;">
                    <a href="{base_url}/dashboard" class="button">Zur Dashboard</a>
                </p>

                <p>Bei Fragen sind wir gerne für dich da!</p>

                <p>Viel Erfolg mit Scripe!</p>

                <div class="footer">
                    <p>&copy; 2024 Scripe - B2B Lead Generation</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
Hallo{' ' + user_name if user_name else ''},

Willkommen bei Scripe - deiner Plattform für B2B Lead Generation!

🎁 Dein Willkommensgeschenk: 10 Credits für deine ersten Recherchen!

Was du mit Scripe machen kannst:

🔍 Intelligente Suche
Finde Unternehmen nach Branche, Standort und Größe.

📞 Verifizierte Kontaktdaten
Erhalte validierte Telefonnummern, E-Mails und Websites.

📊 Qualitäts-Scoring
Jeder Lead wird automatisch nach Datenqualität bewertet.

Starte jetzt: {base_url}/dashboard

Viel Erfolg mit Scripe!

---
Scripe - B2B Lead Generation
        """

        return await self._send_email(to_email, subject, html_content, text_content)


# Singleton instance
email_service = EmailService()
