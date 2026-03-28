"""
服务模块

封装业务逻辑服务，如邮件发送等
"""

import smtplib
import threading
from email.message import EmailMessage

from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_SSL,
    SENDER_EMAIL, SENDER_NAME
)


class EmailService:
    """邮件发送服务"""

    @staticmethod
    def is_configured():
        """检查邮件服务是否已配置"""
        return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)

    @staticmethod
    def send(recipient, subject, body):
        """发送邮件"""
        if not EmailService.is_configured():
            print("[WARN] Email not configured, skip sending")
            return False

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = recipient
        msg.set_content(body)

        try:
            if SMTP_USE_SSL:
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
                    smtp.login(SMTP_USER, SMTP_PASSWORD)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
                    smtp.starttls()
                    smtp.login(SMTP_USER, SMTP_PASSWORD)
                    smtp.send_message(msg)
            return True
        except Exception as e:
            print(f"[ERROR] Send email failed: {e}")
            return False

    @staticmethod
    def send_async(recipient, subject, body):
        """异步发送邮件"""
        thread = threading.Thread(
            target=EmailService.send,
            args=(recipient, subject, body),
            daemon=True
        )
        thread.start()


# 便捷函数
def send_email(recipient, subject, body):
    """发送邮件"""
    return EmailService.send(recipient, subject, body)


def send_email_async(recipient, subject, body):
    """异步发送邮件"""
    EmailService.send_async(recipient, subject, body)