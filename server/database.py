import sqlite3
import hashlib
import os
import datetime
from typing import Optional, Dict, Any

class UserDatabase:
    def __init__(self):
        # 确保 resource 目录存在
        self.db_dir = "resource"
        os.makedirs(self.db_dir, exist_ok=True)
        self.db_path = os.path.join(self.db_dir, "users.db")
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_verified INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                code TEXT NOT NULL,
                code_type TEXT NOT NULL,  -- 'register' or 'reset_password'
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_used INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password: str) -> str:
        """加密密码"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, email: str, password: str) -> bool:
        """创建新用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            password_hash = self.hash_password(password)
            created_at = datetime.datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO users (email, password_hash, created_at, is_verified)
                VALUES (?, ?, ?, 1)
            ''', (email, password_hash, created_at))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False  # 用户已存在
    
    def verify_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户登录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = self.hash_password(password)
        
        cursor.execute('''
            SELECT id, email, created_at FROM users
            WHERE email = ? AND password_hash = ?
        ''', (email, password_hash))
        
        user = cursor.fetchone()
        
        if user:
            # 更新最后登录时间
            cursor.execute('''
                UPDATE users SET last_login = ? WHERE email = ?
            ''', (datetime.datetime.now().isoformat(), email))
            conn.commit()
            
            result = {
                'id': user[0],
                'email': user[1],
                'created_at': user[2]
            }
        else:
            result = None
        
        conn.close()
        return result
    
    def user_exists(self, email: str) -> bool:
        """检查用户是否存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT 1 FROM users WHERE email = ?', (email,))
        exists = cursor.fetchone() is not None
        
        conn.close()
        return exists
    
    def store_verification_code(self, email: str, code: str, code_type: str) -> bool:
        """存储验证码"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            created_at = datetime.datetime.now()
            expires_at = created_at + datetime.timedelta(minutes=10)  # 10分钟过期
            
            cursor.execute('''
                INSERT INTO verification_codes (email, code, code_type, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, code, code_type, created_at.isoformat(), expires_at.isoformat()))
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def verify_code(self, email: str, code: str, code_type: str) -> bool:
        """验证验证码"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = datetime.datetime.now().isoformat()
        
        cursor.execute('''
            SELECT id FROM verification_codes
            WHERE email = ? AND code = ? AND code_type = ? 
            AND is_used = 0 AND expires_at > ?
            ORDER BY created_at DESC LIMIT 1
        ''', (email, code, code_type, current_time))
        
        result = cursor.fetchone()
        
        if result:
            # 标记验证码为已使用
            cursor.execute('''
                UPDATE verification_codes SET is_used = 1 WHERE id = ?
            ''', (result[0],))
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def reset_password(self, email: str, new_password: str) -> bool:
        """重置密码"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            password_hash = self.hash_password(new_password)
            
            cursor.execute('''
                UPDATE users SET password_hash = ? WHERE email = ?
            ''', (password_hash, email))
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

# 全局数据库实例
user_db = UserDatabase()
