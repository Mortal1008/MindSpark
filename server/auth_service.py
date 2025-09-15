import re
from typing import Optional, Dict, Any, Tuple
from .database import user_db
from .email_service import email_service

class AuthService:
    def __init__(self):
        self.db = user_db
        self.email_service = email_service
    
    def validate_email(self, email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """验证密码强度"""
        if len(password) < 6:
            return False, "密码至少需要6位字符"
        if len(password) > 20:
            return False, "密码不能超过20位字符"
        if not re.search(r'[A-Za-z]', password):
            return False, "密码必须包含字母"
        if not re.search(r'\d', password):
            return False, "密码必须包含数字"
        return True, "密码强度符合要求"
    
    def send_register_code(self, email: str) -> Tuple[bool, str]:
        """发送注册验证码"""
        if not self.validate_email(email):
            return False, "邮箱格式不正确"
        
        if self.db.user_exists(email):
            return False, "该邮箱已经注册过了"
        
        code = self.email_service.generate_verification_code()
        
        if self.db.store_verification_code(email, code, 'register'):
            if self.email_service.send_verification_email(email, code, "注册"):
                return True, "验证码已发送到您的邮箱"
            else:
                return False, "验证码发送失败，请检查SMTP配置"
        else:
            return False, "验证码存储失败"
    
    def register_user(self, email: str, password: str, verification_code: str) -> Tuple[bool, str]:
        """用户注册"""
        if not self.validate_email(email):
            return False, "邮箱格式不正确"
        
        is_valid, msg = self.validate_password(password)
        if not is_valid:
            return False, msg
        
        if self.db.user_exists(email):
            return False, "该邮箱已经注册过了"
        
        if not self.db.verify_code(email, verification_code, 'register'):
            return False, "验证码错误或已过期"
        
        if self.db.create_user(email, password):
            return True, "注册成功"
        else:
            return False, "注册失败，请重试"
    
    def login_user(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """用户登录"""
        if not self.validate_email(email):
            return False, "邮箱格式不正确", None
        
        user = self.db.verify_user(email, password)
        if user:
            return True, "登录成功", user
        else:
            return False, "邮箱或密码错误", None
    
    def send_reset_code(self, email: str) -> Tuple[bool, str]:
        """发送密码重置验证码"""
        if not self.validate_email(email):
            return False, "邮箱格式不正确"
        
        if not self.db.user_exists(email):
            return False, "该邮箱尚未注册"
        
        code = self.email_service.generate_verification_code()
        
        if self.db.store_verification_code(email, code, 'reset_password'):
            if self.email_service.send_verification_email(email, code, "密码重置"):
                return True, "验证码已发送到您的邮箱"
            else:
                return False, "验证码发送失败，请检查SMTP配置"
        else:
            return False, "验证码存储失败"
    
    def reset_password(self, email: str, new_password: str, verification_code: str) -> Tuple[bool, str]:
        """重置密码"""
        if not self.validate_email(email):
            return False, "邮箱格式不正确"
        
        is_valid, msg = self.validate_password(new_password)
        if not is_valid:
            return False, msg
        
        if not self.db.user_exists(email):
            return False, "该邮箱尚未注册"
        
        if not self.db.verify_code(email, verification_code, 'reset_password'):
            return False, "验证码错误或已过期"
        
        if self.db.reset_password(email, new_password):
            return True, "密码重置成功"
        else:
            return False, "密码重置失败，请重试"

# 全局认证服务实例
auth_service = AuthService()
