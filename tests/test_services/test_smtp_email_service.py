import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.smtp_email_service import SMTPEmailService
from src.core.config import settings

@pytest.fixture
def mock_smtp_client():
    with patch("src.services.smtp_email_service.SMTPEmailService._smtp_send") as mock_smtp:
        yield mock_smtp

@pytest.mark.asyncio
async def test_send_email_success(mock_smtp_client):
    service = SMTPEmailService()
    
    # Mock settings
    settings.SMTP_HOST = "smtp.test.com"
    settings.SMTP_PORT = 587
    settings.SMTP_USER = "user"
    settings.SMTP_PASSWORD = "password"
    
    success = await service.send_email(
        to_email="test@example.com",
        subject="Test Subject",
        html_content="<p>Test Content</p>"
    )
    
    assert success is True

@pytest.mark.asyncio
async def test_send_password_reset_email(mock_smtp_client):
    service = SMTPEmailService()
    
    with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        success = await service.send_password_reset_email(
            to_email="user@example.com",
            user_name="testuser",
            reset_token="token123"
        )
        
        assert success is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1]["to_email"] == "user@example.com"
        assert "Password Reset" in call_args[1]["subject"]
