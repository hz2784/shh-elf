import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import Optional

# 邮件配置 - 支持多种邮箱服务商
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")  # 发送邮件的邮箱（只需要一个）
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # 邮箱密码或应用密码
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://hz2784.github.io/shh-elf")

# 常用邮箱服务商SMTP配置（自动检测）
def get_smtp_config(email: str):
    """根据邮箱自动检测SMTP配置"""
    if not email:
        return SMTP_SERVER, SMTP_PORT

    domain = email.split('@')[-1].lower()

    smtp_configs = {
        # Gmail
        'gmail.com': ('smtp.gmail.com', 587),
        # QQ邮箱
        'qq.com': ('smtp.qq.com', 587),
        'vip.qq.com': ('smtp.qq.com', 587),
        # 163邮箱
        '163.com': ('smtp.163.com', 994),  # SSL端口
        '126.com': ('smtp.126.com', 994),
        # Outlook/Hotmail
        'outlook.com': ('smtp-mail.outlook.com', 587),
        'hotmail.com': ('smtp-mail.outlook.com', 587),
        'live.com': ('smtp-mail.outlook.com', 587),
        # 企业邮箱
        'sina.com': ('smtp.sina.com', 587),
        'sohu.com': ('smtp.sohu.com', 587),
        # 阿里云邮箱
        'aliyun.com': ('smtp.mxhichina.com', 587),
    }

    return smtp_configs.get(domain, (SMTP_SERVER, SMTP_PORT))

def generate_verification_token() -> str:
    """生成邮箱验证token"""
    return secrets.token_urlsafe(32)

def send_verification_email(to_email: str, username: str, verification_token: str) -> bool:
    """发送邮箱验证邮件"""

    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("邮件服务未配置，跳过发送验证邮件")
        return False

    try:
        # 创建邮件内容
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "SHH-ELF 邮箱验证 / Email Verification"
        msg["From"] = EMAIL_USER
        msg["To"] = to_email

        # 验证链接
        verification_url = f"https://shh-elf.onrender.com/api/verify-email?token={verification_token}"

        # HTML邮件内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Courier New', monospace; background: #000; color: #00ff00; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; border: 2px solid #00ff00; padding: 30px; background: #111; }}
                .header {{ text-align: center; font-size: 24px; margin-bottom: 30px; text-transform: uppercase; }}
                .content {{ line-height: 1.6; margin-bottom: 30px; }}
                .button {{ display: inline-block; background: #00ff00; color: #000; padding: 15px 30px; text-decoration: none; text-transform: uppercase; font-weight: bold; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #00ff00; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">📚 SHH-ELF 邮箱验证</div>

                <div class="content">
                    <p>你好 {username}！</p>
                    <p>欢迎注册 SHH-ELF！请点击下面的按钮验证你的邮箱地址：</p>

                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">验证邮箱 / VERIFY EMAIL</a>
                    </div>

                    <p>如果按钮无法点击，请复制以下链接到浏览器：</p>
                    <p style="color: #666; word-break: break-all;">{verification_url}</p>

                    <p>验证成功后，你将可以：</p>
                    <ul>
                        <li>保存所有生成的推荐到个人历史</li>
                        <li>随时查看和分享之前的推荐</li>
                        <li>享受完整的个性化体验</li>
                    </ul>
                </div>

                <div class="footer">
                    <p>如果你没有注册 SHH-ELF，请忽略此邮件。</p>
                    <p>此链接将在24小时后失效。</p>
                </div>
            </div>
        </body>
        </html>
        """

        # 纯文本版本
        text_content = f"""
        SHH-ELF 邮箱验证

        你好 {username}！

        欢迎注册 SHH-ELF！请访问以下链接验证你的邮箱地址：

        {verification_url}

        验证成功后，你将可以保存和查看所有推荐历史。

        如果你没有注册 SHH-ELF，请忽略此邮件。
        此链接将在24小时后失效。
        """

        # 添加邮件内容
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        msg.attach(part1)
        msg.attach(part2)

        # 自动检测发送邮箱的SMTP配置
        smtp_server, smtp_port = get_smtp_config(EMAIL_USER)

        # 发送邮件
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"验证邮件已发送到: {to_email}")
        return True

    except Exception as e:
        print(f"发送邮件失败: {str(e)}")
        return False

def send_welcome_email(to_email: str, username: str) -> bool:
    """发送欢迎邮件（邮箱验证成功后）"""

    if not EMAIL_USER or not EMAIL_PASSWORD:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🎉 欢迎来到 SHH-ELF！"
        msg["From"] = EMAIL_USER
        msg["To"] = to_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Courier New', monospace; background: #000; color: #00ff00; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; border: 2px solid #00ff00; padding: 30px; background: #111; }}
                .header {{ text-align: center; font-size: 24px; margin-bottom: 30px; text-transform: uppercase; }}
                .content {{ line-height: 1.6; }}
                .button {{ display: inline-block; background: #00ff00; color: #000; padding: 15px 30px; text-decoration: none; text-transform: uppercase; font-weight: bold; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">🎉 欢迎来到 SHH-ELF！</div>

                <div class="content">
                    <p>{username}，你的邮箱已成功验证！</p>
                    <p>现在你可以享受 SHH-ELF 的完整功能：</p>

                    <ul>
                        <li>🎯 生成个性化书籍推荐</li>
                        <li>💾 自动保存推荐历史</li>
                        <li>🔗 随时分享你的推荐</li>
                        <li>📚 建立你的推荐收藏</li>
                    </ul>

                    <div style="text-align: center;">
                        <a href="{FRONTEND_URL}" class="button">开始使用 SHH-ELF</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        part = MIMEText(html_content, "html")
        msg.attach(part)

        smtp_server, smtp_port = get_smtp_config(EMAIL_USER)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"发送欢迎邮件失败: {str(e)}")
        return False