import bcrypt
import streamlit as st
from database import (
    init_db, create_user, get_user_by_email,
    save_credentials, get_credentials, has_credentials
)

init_db()


# ── Password utils ────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ── Session helpers ───────────────────────────────────────────
def is_logged_in() -> bool:
    return st.session_state.get("user_id") is not None

def get_current_user() -> dict | None:
    if not is_logged_in():
        return None
    return {
        "id": st.session_state["user_id"],
        "email": st.session_state["user_email"]
    }

def login_user(user_id: int, email: str):
    st.session_state["user_id"] = user_id
    st.session_state["user_email"] = email
    # Clear any stale data from a previous session
    for key in ["tickets", "result", "chat_history", "projects", "confluence_spaces"]:
        st.session_state.pop(key, None)

def logout_user():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ── Auth UI ───────────────────────────────────────────────────
def render_auth_page():
    """Renders login/signup page. Returns True if user just authenticated."""
    st.markdown("<h1>🧠 AI Sprint Manager</h1>", unsafe_allow_html=True)
    st.markdown('<p style="color:#6b7280;margin-top:-0.5rem;">Connect your Jira. Let AI do the sprint work.</p>', unsafe_allow_html=True)
    st.markdown("---")

    tab_login, tab_signup = st.tabs(["🔑 Log In", "✨ Sign Up"])

    with tab_login:
        st.markdown("#### Welcome back")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Log In", key="btn_login"):
            if not email or not password:
                st.error("Please fill in all fields.")
            else:
                user = get_user_by_email(email)
                if user and verify_password(password, user["password_hash"]):
                    login_user(user["id"], user["email"])
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

    with tab_signup:
        st.markdown("#### Create your account")
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password (min 8 chars)", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")

        if st.button("Create Account", key="btn_signup"):
            if not new_email or not new_password or not confirm_password:
                st.error("Please fill in all fields.")
            elif len(new_password) < 8:
                st.error("Password must be at least 8 characters.")
            elif new_password != confirm_password:
                st.error("Passwords don't match.")
            else:
                user_id = create_user(new_email, hash_password(new_password))
                if user_id:
                    login_user(user_id, new_email)
                    st.success("Account created!")
                    st.rerun()
                else:
                    st.error("An account with this email already exists.")


# ── Credentials setup UI ──────────────────────────────────────
def render_credentials_setup():
    """Shown after signup/login if user hasn't connected Jira yet."""
    user = get_current_user()
    st.markdown("<h1>🔗 Connect Your Jira Account</h1>", unsafe_allow_html=True)
    st.markdown('<p style="color:#6b7280;">You only need to do this once. Your API token is stored encrypted.</p>', unsafe_allow_html=True)
    st.markdown("---")

    with st.expander("ℹ️ How to find your Jira API token", expanded=False):
        st.markdown("""
        1. Go to [id.atlassian.net/manage-profile/security/api-tokens](https://id.atlassian.net/manage-profile/security/api-tokens)
        2. Click **Create API token**
        3. Give it a name (e.g. "AI Sprint Manager") and copy the token
        4. Your Jira URL is the base URL of your Jira instance, e.g. `https://yourcompany.atlassian.net`
        """)

    jira_url = st.text_input("Jira URL", placeholder="https://yourcompany.atlassian.net")
    jira_email = st.text_input("Jira Email", placeholder="you@yourcompany.com")
    jira_token = st.text_input("Jira API Token", type="password")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("💾 Save & Connect"):
            if not jira_url or not jira_email or not jira_token:
                st.error("Please fill in all fields.")
            else:
                # Quick validation — try fetching projects
                import requests
                try:
                    resp = requests.get(
                        f"{jira_url.rstrip('/')}/rest/api/3/project",
                        auth=(jira_email, jira_token),
                        timeout=5
                    )
                    if resp.status_code == 200:
                        save_credentials(user["id"], jira_url.rstrip("/"), jira_email, jira_token)
                        st.success("✅ Connected! Loading your workspace...")
                        st.rerun()
                    elif resp.status_code == 401:
                        st.error("❌ Invalid credentials. Check your email and API token.")
                    else:
                        st.error(f"❌ Could not connect ({resp.status_code}). Check your Jira URL.")
                except Exception as e:
                    st.error(f"❌ Connection failed: {e}")
    with col2:
        if st.button("🚪 Log Out Instead"):
            logout_user()
            st.rerun()
