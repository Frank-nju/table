"""
服务模块

导出各种业务服务
"""

from services.email import EmailService, send_email, send_email_async

__all__ = ["EmailService", "send_email", "send_email_async"]