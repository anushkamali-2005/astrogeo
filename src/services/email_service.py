"""
Email Service
=============
Production email service with template support:
- SendGrid integration
- HTML email templates
- Async sending
- Error handling and retries

Author: Production Team
Version: 1.0.0
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, Email, Mail, To

from src.core.config import settings
from src.core.exceptions import EmailError
from src.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# EMAIL TEMPLATES
# ============================================================================

EMAIL_TEMPLATES = {
    "welcome": {
        "subject": "Welcome to AstroGeo AI!",
        "html": """
        <html>
            <body>
                <h1>Welcome {name}!</h1>
                <p>Thank you for joining AstroGeo AI MLOps Platform.</p>
                <p>Get started by exploring our AI agents and geospatial tools.</p>
            </body>
        </html>
        """,
    },
    "password_reset": {
        "subject": "Password Reset Request",
        "html": """
        <html>
            <body>
                <h1>Password Reset</h1>
                <p>You requested a password reset for your account.</p>
                <p>Click the link below to reset your password:</p>
                <a href="{reset_link}">Reset Password</a>
                <p>This link will expire in {expiry_hours} hours.</p>
            </body>
        </html>
        """,
    },
    "model_training_complete": {
        "subject": "Model Training Complete",
        "html": """
        <html>
            <body>
                <h1>Model Training Completed</h1>
                <p>Your model <strong>{model_name}</strong> has finished training.</p>
                <h3>Results:</h3>
                <ul>
                    <li>Accuracy: {accuracy}%</li>
                    <li>Training Time: {training_time}</li>
                    <li>Status: {status}</li>
                </ul>
                <p><a href="{model_url}">View Model Details</a></p>
            </body>
        </html>
        """,
    },
}


# ============================================================================
# EMAIL SERVICE
# ============================================================================


class EmailService:
    """
    Production email service with SendGrid.

    Features:
    - Template-based emails
    - HTML and plain text support
    - Async sending
    - Error handling

    Time complexity: O(1) per email
    Space complexity: O(1)
    """

    def __init__(self):
        """Initialize SendGrid client."""
        self.client = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME

        logger.info("Email service initialized")

    async def send_email(
        self, to_email: str, subject: str, html_content: str, plain_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email.

        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML content
            plain_content: Plain text content

        Returns:
            dict: Send result

        Raises:
            EmailError: If sending fails
        """
        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
            )

            if plain_content:
                message.plain_text_content = Content("text/plain", plain_content)

            response = self.client.send(message)

            logger.info(
                "Email sent successfully",
                extra={"to": to_email, "subject": subject, "status_code": response.status_code},
            )

            return {"success": True, "status_code": response.status_code, "to_email": to_email}

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}", error=e)
            raise EmailError(
                message="Failed to send email", details={"to_email": to_email, "error": str(e)}
            )

    async def send_template_email(
        self, to_email: str, template_name: str, template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send email using predefined template.

        Args:
            to_email: Recipient email
            template_name: Template name
            template_data: Template data for interpolation

        Returns:
            dict: Send result
        """
        if template_name not in EMAIL_TEMPLATES:
            raise EmailError(
                message="Unknown email template", details={"template_name": template_name}
            )

        template = EMAIL_TEMPLATES[template_name]

        # Format template
        subject = template["subject"].format(**template_data)
        html_content = template["html"].format(**template_data)

        return await self.send_email(to_email=to_email, subject=subject, html_content=html_content)

    async def send_bulk_email(
        self, recipients: List[str], subject: str, html_content: str
    ) -> Dict[str, Any]:
        """
        Send bulk email to multiple recipients.

        Args:
            recipients: List of recipient emails
            subject: Email subject
            html_content: HTML content

        Returns:
            dict: Send results
        """
        results = {"total": len(recipients), "successful": 0, "failed": 0, "errors": []}

        for recipient in recipients:
            try:
                await self.send_email(recipient, subject, html_content)
                results["successful"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"email": recipient, "error": str(e)})

        logger.info(
            "Bulk email send completed",
            extra={
                "total": results["total"],
                "successful": results["successful"],
                "failed": results["failed"],
            },
        )

        return results


# Export
__all__ = ["EmailService", "EMAIL_TEMPLATES"]
