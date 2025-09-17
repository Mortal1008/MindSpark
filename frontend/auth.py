import streamlit as st
import time
from server.auth_service import auth_service


# -------------------------- 核心修改：动态注入CSS --------------------------
def inject_global_css():
    """根据登录状态动态注入全局CSS样式（登录后移除目标按钮样式）"""
    # 1. 基础样式（所有状态都保留，不含目标按钮样式）
    base_css = """
    <style>
    .auth-title {
        text-align: center;
        color: #2E86AB;
        font-size: 2rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
    }
    
    .auth-subtitle {
        text-align: center;
        color: #666;
        font-size: 0.9rem;
        margin-bottom: 2rem;
    }
    
    .code-button {
        margin-top: 0.5rem;
    }
    
    .link-button {
        background: none !important;
        color: #2E86AB !important;
        border: none !important;
        text-decoration: underline !important;
        cursor: pointer !important;
        font-size: 0.9rem !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    .form-section {
        margin-bottom: 1.5rem;
    }
    
    .divider {
        text-align: center;
        margin: 1.5rem 0;
        color: #999;
        position: relative;
    }
    
    .divider::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        height: 1px;
        background: #ddd;
        z-index: 1;
    }
    
    .divider span {
        background: white;
        padding: 0 1rem;
        position: relative;
        z-index: 2;
    }
    
    .success-message {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.75rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .error-message {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    """

    # 2. 未登录时追加目标按钮样式（登录后自动不加载）
    if "user" not in st.session_state:  # 仅未登录状态加载该样式
        login_button_css = """
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(46, 134, 171, 0.3);
    }
        """
        full_css = base_css + login_button_css
    else:
        full_css = base_css  # 登录后仅加载基础样式（无目标按钮样式）

    # 3. 注入最终CSS
    st.markdown(full_css, unsafe_allow_html=True)


# -------------------------- 以下函数保持不变 --------------------------
def show_message(message, is_error=False):
    """显示消息"""
    if is_error:
        st.markdown(
            f'<div class="error-message">{message}</div>', unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="success-message">{message}</div>', unsafe_allow_html=True
        )


def login_form():
    """登录表单"""
    st.markdown('<div class="auth-title">登录 MindSpark</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="auth-subtitle">使用您的邮箱账号登录</div>', unsafe_allow_html=True
    )

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("邮箱地址", placeholder="请输入您的邮箱")
        password = st.text_input("密码", type="password", placeholder="请输入您的密码")

        col1, col2 = st.columns([1, 1])
        with col1:
            login_clicked = st.form_submit_button("登录", use_container_width=True)
        with col2:
            forgot_clicked = st.form_submit_button(
                "忘记密码", use_container_width=True, type="secondary"
            )

        if login_clicked:
            if email and password:
                success, message, user = auth_service.login_user(email, password)
                if success:
                    st.session_state["user"] = user  # 登录成功后设置user状态
                    show_message("登录成功！正在跳转...")
                    time.sleep(1)
                    st.rerun()
                else:
                    show_message(message, is_error=True)
            else:
                show_message("请填写完整的登录信息", is_error=True)

        if forgot_clicked:
            st.session_state.auth_mode = "forgot_password"
            st.rerun()

    st.markdown(
        '<div class="divider"><span>还没有账号？</span></div>', unsafe_allow_html=True
    )

    if st.button("立即注册", use_container_width=True, key="goto_register"):
        st.session_state.auth_mode = "register"
        st.rerun()


def register_form():
    """注册表单（保持原逻辑不变）"""
    st.markdown('<div class="auth-title">注册 MindSpark</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="auth-subtitle">创建您的新账号</div>', unsafe_allow_html=True
    )

    with st.form("register_form", clear_on_submit=False):
        email = st.text_input("邮箱地址", placeholder="请输入您的邮箱")

        # 验证码行
        st.write("验证码")
        col1, col2 = st.columns([2, 1])
        with col1:
            verification_code = st.text_input(
                "验证码", placeholder="请输入验证码", label_visibility="collapsed"
            )
        with col2:
            send_code_clicked = st.form_submit_button(
                "发送验证码", use_container_width=True
            )

        password = st.text_input(
            "密码", type="password", placeholder="至少6位，包含字母和数字"
        )
        confirm_password = st.text_input(
            "确认密码", type="password", placeholder="请再次输入密码"
        )

        register_clicked = st.form_submit_button("注册", use_container_width=True)

        # 处理发送验证码
        if send_code_clicked:
            if email:
                success, message = auth_service.send_register_code(email)
                if success:
                    show_message(message)
                else:
                    show_message(message, is_error=True)
            else:
                show_message("请先输入邮箱地址", is_error=True)

        # 处理注册
        if register_clicked:
            if email and verification_code and password and confirm_password:
                if password != confirm_password:
                    show_message("两次输入的密码不一致", is_error=True)
                else:
                    success, message = auth_service.register_user(
                        email, password, verification_code
                    )
                    if success:
                        show_message("注册成功！请登录")
                        time.sleep(1)
                        st.session_state.auth_mode = "login"
                        st.rerun()
                    else:
                        show_message(message, is_error=True)
            else:
                show_message("请填写完整的注册信息", is_error=True)

    st.markdown(
        '<div class="divider"><span>已有账号？</span></div>', unsafe_allow_html=True
    )

    if st.button("返回登录", use_container_width=True, key="goto_login"):
        st.session_state.auth_mode = "login"
        st.rerun()


def forgot_password_form():
    """忘记密码表单（保持原逻辑不变）"""
    st.markdown('<div class="auth-title">重置密码</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="auth-subtitle">通过邮箱验证重置您的密码</div>',
        unsafe_allow_html=True,
    )

    with st.form("forgot_password_form", clear_on_submit=False):
        email = st.text_input("邮箱地址", placeholder="请输入您的注册邮箱")

        # 验证码行
        st.write("验证码")
        col1, col2 = st.columns([2, 1])
        with col1:
            verification_code = st.text_input(
                "验证码", placeholder="请输入验证码", label_visibility="collapsed"
            )
        with col2:
            send_reset_code_clicked = st.form_submit_button(
                "发送验证码", use_container_width=True
            )

        new_password = st.text_input(
            "新密码", type="password", placeholder="至少6位，包含字母和数字"
        )
        confirm_new_password = st.text_input(
            "确认新密码", type="password", placeholder="请再次输入新密码"
        )

        reset_clicked = st.form_submit_button("重置密码", use_container_width=True)

        # 处理发送验证码
        if send_reset_code_clicked:
            if email:
                success, message = auth_service.send_reset_code(email)
                if success:
                    show_message(message)
                else:
                    show_message(message, is_error=True)
            else:
                show_message("请先输入邮箱地址", is_error=True)

        # 处理密码重置
        if reset_clicked:
            if email and verification_code and new_password and confirm_new_password:
                if new_password != confirm_new_password:
                    show_message("两次输入的密码不一致", is_error=True)
                else:
                    success, message = auth_service.reset_password(
                        email, new_password, verification_code
                    )
                    if success:
                        show_message("密码重置成功！请使用新密码登录")
                        time.sleep(1)
                        st.session_state.auth_mode = "login"
                        st.rerun()
                    else:
                        show_message(message, is_error=True)
            else:
                show_message("请填写完整的重置信息", is_error=True)

    st.markdown(
        '<div class="divider"><span>想起密码了？</span></div>', unsafe_allow_html=True
    )

    if st.button("返回登录", use_container_width=True, key="back_to_login"):
        st.session_state.auth_mode = "login"
        st.rerun()


def require_login_ui():
    """登录界面主函数（保持原逻辑不变）"""
    # 初始化认证模式
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    # 先注入CSS（关键：每次渲染都先执行CSS注入，确保状态生效）
    inject_global_css()

    # 创建居中的认证容器
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.session_state.auth_mode == "login":
            login_form()
        elif st.session_state.auth_mode == "register":
            register_form()
        elif st.session_state.auth_mode == "forgot_password":
            forgot_password_form()


def logout():
    """登出函数（保持原逻辑不变，登出后清除user状态，恢复样式）"""
    if "user" in st.session_state:
        del st.session_state["user"]  # 清除登录状态，下次渲染会重新加载按钮样式
    if "auth_mode" in st.session_state:
        del st.session_state["auth_mode"]
    st.rerun()
