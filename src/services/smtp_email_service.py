"""
SMTP Email Service
==================
Production email service using SMTP for broader compatibility.

Features:
- SMTP integration
- HTML email templates
- Async sending
- Retry logic
- Template rendering with Jinja2

Author: Production Team
Version: 1.0.0
"""

from typing import Dict, Any, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import asyncio
from jinja2 import Environment, FileSystemLoader

from src.core.config import settings
from src.core.logging import get_logger
from src.core.exceptions import EmailError

logger = get_logger(__name__)


class SMTPEmailService:
    """
    Email service for sending transactional emails via SMTP.
    
    Features:
    - SMTP configuration from settings
    - HTML template rendering
    - Async email sending
    - Retry on failure
    - Fallback to inline HTML if templates not found
    """
    
    def __init__(self):
        """Initialize email service."""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_TLS
        self.use_ssl = settings.SMTP_SSL
        
        # Setup Jinja2 for templates
        template_dir = Path(settings.EMAIL_TEMPLATES_DIR)
        if template_dir.exists():
            self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))
            logger.info(f"Email templates loaded from: {template_dir}")
        else:
            self.jinja_env = None
            logger.warning(f"Email template directory not found: {template_dir}")
        
        logger.info(
            "SMTP Email service initialized",
            extra={
                "smtp_host": self.smtp_host,
                "smtp_port": self.smtp_port,
                "from_email": self.from_email
            }
        )
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email with retry logic.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text fallback
            
        Returns:
            bool: True if sent successfully
            
        Raises:
            EmailError: If email fails after retries
        """
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                await self._send_email_smtp(to_email, subject, html_content, text_content)
                
                logger.info(
                    "Email sent successfully",
                    extra={
                        "to_email": to_email,
                        "subject": subject,
                        "attempt": attempt + 1
                    }
                )
                return True
                
            except Exception as e:
                logger.warning(
                    f"Email send attempt {attempt + 1} failed",
                    extra={"error": str(e), "to_email": to_email}
                )
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(
                        "Email send failed after all retries",
                        error=e,
                        extra={"to_email": to_email}
                    )
                    raise EmailError(
                        message="Failed to send email",
                        details={
                            "to_email": to_email,
                            "subject": subject,
                            "error": str(e)
                        }
                    )
        
        return False
    
    async def _send_email_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ):
        """
        Send email via SMTP.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML body
            text_content: Plain text body
        """
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email
        
        # Add plain text version
        if text_content:
            part1 = MIMEText(text_content, 'plain')
            msg.attach(part1)
        
        # Add HTML version
        part2 = MIMEText(html_content, 'html')
        msg.attach(part2)
        
        # Send via SMTP in thread pool (blocking operation)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._smtp_send, msg)
    
    def _smtp_send(self, msg: MIMEMultipart):
        """Blocking SMTP send operation."""
        try:
            if self.use_ssl:
                # Use SSL from the start
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                # Use TLS (STARTTLS)
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()
                    
                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)
                    
                    server.send_message(msg)
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            raise
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render email template.
        
        Args:
            template_name: Template filename
            context: Template variables
            
        Returns:
            str: Rendered HTML
        """
        if not self.jinja_env:
            raise EmailError(
                message="Email templates not configured",
                details={"template": template_name}
            )
        
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(
                "Template rendering failed",
                error=e,
                extra={"template": template_name}
            )
            raise EmailError(
                message="Failed to render email template",
                details={"template": template_name, "error": str(e)}
            )
    
    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        user_name: str
    ) -> bool:
        """
        Send password reset email.
        
        Args:
            to_email: User email
            reset_token: Password reset token
            user_name: User's name
            
        Returns:
            bool: True if sent
        """
        reset_link = f"{settings.PASSWORD_RESET_URL}?token={reset_token}"
        
        # Try to use template, fallback to simple HTML
        if self.jinja_env:
            try:
                html_content = self.render_template(
                    'password_reset.html',
                    {
                        'user_name': user_name,
                        'reset_link': reset_link,
                        'app_name': settings.APP_NAME,
                        'expiry_hours': 1
                    }
                )
            except Exception as e:
                logger.warning(f"Template rendering failed, using fallback: {e}")
                html_content = self._get_password_reset_fallback_html(user_name, reset_link)
        else:
            # Fallback HTML
            html_content = self._get_password_reset_fallback_html(user_name, reset_link)
        
        text_content = f"""
Password Reset Request

Hello {user_name},

You requested to reset your password. Visit this link:
{reset_link}

This link expires in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
{settings.APP_NAME} Team
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Password Reset - {settings.APP_NAME}",
            html_content=html_content,
            text_content=text_content
        )
    
    def _get_password_reset_fallback_html(self, user_name: str, reset_link: str) -> str:
        """Generate fallback HTML for password reset email."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0;">Password Reset Request</h1>
    </div>
    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
        <p style="font-size: 16px;">Hello <strong>{user_name}</strong>,</p>
        <p style="font-size: 16px;">You requested to reset your password for your {settings.APP_NAME} account.</p>
        <p style="font-size: 16px;">Click the button below to reset your password:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Reset Password</a>
        </div>
        <p style="font-size: 14px; color: #666;">This link will expire in <strong>1 hour</strong>.</p>
        <p style="font-size: 14px; color: #666;">If you didn't request this password reset, please ignore this email or contact support if you have concerns.</p>
        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
        <p style="font-size: 12px; color: #999; text-align: center;">
            This email was sent by {settings.APP_NAME}<br>
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{reset_link}" style="color: #667eea; word-break: break-all;">{reset_link}</a>
        </p>
    </div>
</body>
</html>
        """
    
    async def send_welcome_email(
        self,
        to_email: str,
        user_name: str
    ) -> bool:
        """Send welcome email to new user."""
        if self.jinja_env:
            try:
                html_content = self.render_template(
                    'welcome.html',
                    {
                        'user_name': user_name,
                        'app_name': settings.APP_NAME
                    }
                )
            except Exception:
                html_content = self._get_welcome_fallback_html(user_name)
        else:
            html_content = self._get_welcome_fallback_html(user_name)
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Welcome to {settings.APP_NAME}",
            html_content=html_content
        )
    
    def _get_welcome_fallback_html(self, user_name: str) -> str:
        """Generate fallback HTML for welcome email."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0;">Welcome to {settings.APP_NAME}!</h1>
    </div>
    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
        <p style="font-size: 16px;">Hello <strong>{user_name}</strong>,</p>
        <p style="font-size: 16px;">Thank you for registering with {settings.APP_NAME}. Your account has been created successfully!</p>
        <p style="font-size: 16px;">You can now start using our platform to:</p>
        <ul style="font-size: 16px;">
            <li>Deploy intelligent AI agents</li>
            <li>Perform geospatial analysis</li>
            <li>Track ML experiments with MLflow</li>
            <li>Build production-ready ML models</li>
        </ul>
        <p style="font-size: 16px;">If you have any questions, don't hesitate to reach out to our support team.</p>
        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
        <p style="font-size: 12px; color: #999; text-align: center;">
            Best regards,<br>
            The {settings.APP_NAME} Team
        </p>
    </div>
</body>
</html>
        """


# Create singleton instance
smtp_email_service = SMTPEmailService()


# Export
__all__ = ["SMTPEmailService", "smtp_email_service"]
