import secrets
import os
from typing import Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

# SendGrid配置
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@shhelf.com")  # 需要在SendGrid验证的发送者邮箱
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://hz2784.github.io/shh-elf")

def generate_verification_token() -> str:
    """生成邮箱验证token"""
    return secrets.token_urlsafe(32)

def send_verification_email_sendgrid(to_email: str, username: str, verification_token: str) -> bool:
    """使用SendGrid发送邮箱验证邮件"""

    if not SENDGRID_API_KEY:
        print("SendGrid API Key未配置，跳过发送验证邮件")
        return False

    try:
        # 验证链接
        verification_url = f"https://shh-elf.onrender.com/api/verify-email?token={verification_token}"

        # 创建邮件内容
        from_email = Email(FROM_EMAIL)
        to_email_obj = To(to_email)
        subject = "SHH-ELF Email Verification"

        # HTML邮件内容 - 改为清晰易读的样式
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background: #f5f5f5; color: #333; padding: 20px; margin: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 40px; background: #ffffff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; font-size: 28px; margin-bottom: 30px; color: #2c3e50; font-weight: bold; }}
                .content {{ line-height: 1.8; margin-bottom: 30px; color: #444; }}
                .button {{ display: inline-block; background: #3498db; color: #ffffff; padding: 16px 32px; text-decoration: none; font-weight: bold; margin: 20px 0; border-radius: 6px; font-size: 16px; }}
                .button:hover {{ background: #2980b9; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 14px; color: #777; }}
                .url-box {{ background: #f8f9fa; padding: 15px; border: 1px solid #e9ecef; border-radius: 4px; font-family: monospace; word-break: break-all; font-size: 14px; }}
                ul {{ padding-left: 20px; }}
                li {{ margin-bottom: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">SHH-ELF Email Verification</div>

                <div class="content">
                    <p>Hello <strong>{username}</strong>!</p>
                    <p>Welcome to <strong>SHH-ELF</strong>! Please click the button below to verify your email address:</p>

                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">VERIFY EMAIL</a>
                    </div>

                    <p>If the button doesn't work, please copy and paste this link into your browser:</p>
                    <div class="url-box">{verification_url}</div>

                    <p><strong>After verification, you will be able to:</strong></p>
                    <ul>
                        <li>Save all generated recommendations to your personal history</li>
                        <li>View and share your previous recommendations anytime</li>
                        <li>Enjoy the complete personalized experience</li>
                    </ul>
                </div>

                <div class="footer">
                    <p>If you didn't sign up for SHH-ELF, please ignore this email.</p>
                    <p>This verification link will expire in 24 hours.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # 纯文本版本
        plain_text_content = f"""
        SHH-ELF Email Verification

        Hello {username}!

        Welcome to SHH-ELF! Please visit the following link to verify your email address:

        {verification_url}

        After verification, you will be able to save and view all recommendation history.

        If you didn't sign up for SHH-ELF, please ignore this email.
        This verification link will expire in 24 hours.
        """

        # 创建邮件对象
        mail = Mail(
            from_email=from_email,
            to_emails=to_email_obj,
            subject=subject,
            plain_text_content=plain_text_content,
            html_content=html_content
        )

        # 发送邮件
        sg = SendGridAPIClient(api_key=SENDGRID_API_KEY)
        response = sg.send(mail)

        print(f"SendGrid验证邮件已发送到: {to_email}, 状态码: {response.status_code}")
        return True

    except Exception as e:
        print(f"SendGrid发送邮件失败: {str(e)}")
        return False

def send_welcome_email_sendgrid(to_email: str, username: str) -> bool:
    """使用SendGrid发送欢迎邮件（邮箱验证成功后）"""

    if not SENDGRID_API_KEY:
        return False

    try:
        from_email = Email(FROM_EMAIL)
        to_email_obj = To(to_email)
        subject = "Welcome to SHH-ELF!"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background: #f5f5f5; color: #333; padding: 20px; margin: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 40px; background: #ffffff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; font-size: 28px; margin-bottom: 30px; color: #27ae60; font-weight: bold; }}
                .content {{ line-height: 1.8; color: #444; }}
                .button {{ display: inline-block; background: #27ae60; color: #ffffff; padding: 16px 32px; text-decoration: none; font-weight: bold; margin: 20px 0; border-radius: 6px; font-size: 16px; }}
                .button:hover {{ background: #229954; }}
                ul {{ padding-left: 20px; }}
                li {{ margin-bottom: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">Welcome to SHH-ELF!</div>

                <div class="content">
                    <p><strong>{username}</strong>, your email has been successfully verified!</p>
                    <p>You can now enjoy the complete features of <strong>SHH-ELF</strong>:</p>

                    <ul>
                        <li>Generate personalized book recommendations</li>
                        <li>Automatically save recommendation history</li>
                        <li>Share your recommendations anytime</li>
                        <li>Build your recommendation collection</li>
                    </ul>

                    <div style="text-align: center;">
                        <a href="{FRONTEND_URL}" class="button">START USING SHH-ELF</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        mail = Mail(
            from_email=from_email,
            to_emails=to_email_obj,
            subject=subject,
            html_content=html_content
        )

        sg = SendGridAPIClient(api_key=SENDGRID_API_KEY)
        response = sg.send(mail)

        print(f"SendGrid欢迎邮件已发送到: {to_email}, 状态码: {response.status_code}")
        return True

    except Exception as e:
        print(f"SendGrid发送欢迎邮件失败: {str(e)}")
        return False