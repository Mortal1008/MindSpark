import smtplib
import os
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = int(os.getenv('SMTP_PORT'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_pass = os.getenv('SMTP_PASS')
    
    def generate_verification_code(self, length: int = 6) -> str:
        """生成验证码"""
        return ''.join(random.choices(string.digits, k=length))
    
    def send_verification_email(self, to_email: str, code: str, purpose: str = "注册") -> bool:
        """发送验证码邮件"""
        if not all([self.smtp_user, self.smtp_pass]):
            print("SMTP配置不完整，无法发送邮件")
            return False
        try:
            # 创建邮件内容
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = to_email
            msg['Subject'] = f"MindSpark - {purpose}验证码"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2E86AB; text-align: center;">MindSpark 验证码</h2>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center;">
                        <p>您好！</p>
                        <p>您正在进行{purpose}操作，验证码为：</p>
                        <div style="font-size: 24px; font-weight: bold; color: #2E86AB; letter-spacing: 3px; margin: 20px 0;">
                            {code}
                        </div>
                        <p style="color: #666; font-size: 14px;">验证码有效期为10分钟，请及时使用。</p>
                    </div>
                    <p style="margin-top: 20px; font-size: 12px; color: #999; text-align: center;">
                        如果这不是您本人的操作，请忽略此邮件。
                    </p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # 发送邮件
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            
            server.login(self.smtp_user, self.smtp_pass)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"发送邮件失败: {e}")
            return False

# 全局邮件服务实例
email_service = EmailService()
