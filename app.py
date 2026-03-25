import streamlit as st
import json
import re
from auth import is_logged_in, get_current_user, logout_user, render_auth_page, render_credentials_setup
from database import get_credentials, has_credentials
from jira_client import get_jira_tickets, get_jira_projects
from confluence_client import get_confluence_spaces
from rag import index_confluence_pages
from main import run_pipeline
from chat_agent import chat

# ── MUST be the very first Streamlit call ─────────────────────
st.set_page_config(page_title="AI Sprint Manager", layout="wide", page_icon="🧠")

# ── Global CSS ────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .main { background-color: #0f1117; }
    .block-container { padding: 2rem 3rem; }
    h1 { font-size: 1.8rem !important; font-weight: 600 !important; color: #ffffff !important; }
    .subtitle { color: #6b7280; font-size: 0.9rem; margin-top: -0.5rem; margin-bottom: 2rem; }
    .ticket-card { background: #1a1d27; border: 1px solid #2d3148; border-radius: 12px; padding: 1.2rem 1.5rem; margin-bottom: 1rem; }
    .ticket-id { font-family: 'DM Mono', monospace; color: #6366f1; font-size: 0.8rem; font-weight: 500; }
    .ticket-title { color: #f1f5f9; font-size: 1rem; font-weight: 500; margin: 0.3rem 0; }
    .ticket-desc { color: #94a3b8; font-size: 0.85rem; line-height: 1.5; }
    .priority-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 0.75rem; }
    .p0 { background: #fee2e2; color: #dc2626; }
    .p1 { background: #ffedd5; color: #ea580c; }
    .p2 { background: #fef9c3; color: #ca8a04; }
    .p3 { background: #dcfce7; color: #16a34a; }
    .section-card { background: #1a1d27; border: 1px solid #2d3148; border-radius: 12px; padding: 1.5rem; height: 100%; }
    .section-title { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #6b7280; margin-bottom: 1rem; }
    .reason-text { color: #e2e8f0; font-size: 0.9rem; line-height: 1.6; background: #12141e; border-left: 3px solid #6366f1; padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; }
    .task-item { display: flex; gap: 0.75rem; align-items: flex-start; padding: 0.6rem 0; border-bottom: 1px solid #2d3148; color: #cbd5e1; font-size: 0.875rem; }
    .task-item:last-child { border-bottom: none; }
    .task-num { background: #2d3148; color: #6366f1; font-family: 'DM Mono', monospace; font-size: 0.7rem; font-weight: 600; width: 22px; height: 22px; border-radius: 6px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 1px; }
    .test-case { background: #12141e; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; }
    .test-case-desc { color: #e2e8f0; font-size: 0.85rem; font-weight: 500; }
    .test-case-result { color: #6b7280; font-size: 0.8rem; margin-top: 0.25rem; }
    .risk-item { background: #1e1215; border: 1px solid #3d1f24; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; }
    .risk-desc { color: #fca5a5; font-size: 0.85rem; font-weight: 500; }
    .risk-mitigation { color: #6b7280; font-size: 0.8rem; margin-top: 0.25rem; }
    .stButton > button { background: #6366f1 !important; color: white !important; border: none !important; border-radius: 8px !important; padding: 0.5rem 1.5rem !important; font-family: 'DM Sans', sans-serif !important; font-weight: 500 !important; width: 100%; }
    .stButton > button:hover { background: #4f46e5 !important; }
    .stSelectbox > div > div { background: #1a1d27 !important; border-color: #2d3148 !important; color: #f1f5f9 !important; }
    .stSlider > div { color: #f1f5f9; }
    div[data-testid="stSidebar"] { background: #12141e !important; border-right: 1px solid #2d3148; }
    .chat-message { padding: 0.75rem 1rem; border-radius: 10px; margin-bottom: 0.75rem; font-size: 0.9rem; line-height: 1.6; }
    .chat-user { background: #2d3148; color: #e2e8f0; margin-left: 3rem; }
    .chat-assistant { background: #1a1d27; border: 1px solid #2d3148; color: #e2e8f0; margin-right: 3rem; }
    .chat-label { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.3rem; }
    .stTabs [data-baseweb="tab-list"] { background: #12141e; border-radius: 8px; padding: 0.25rem; }
    .stTabs [data-baseweb="tab"] { color: #6b7280 !important; border-radius: 6px; }
    .stTabs [aria-selected="true"] { background: #1a1d27 !important; color: #f1f5f9 !important; }
    .user-badge { background: #1a1d27; border: 1px solid #2d3148; border-radius: 8px; padding: 0.5rem 0.75rem; font-size: 0.8rem; color: #94a3b8; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)


# ── Helper functions ───────────────────────────────────────────
def parse_json_from_output(text):
    try:
        text = str(text)
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        pass
    return None


def get_priority_class(priority):
    p = priority.upper()
    if "P0" in p: return "p0"
    if "P1" in p: return "p1"
    if "P2" in p: return "p2"
    return "p3"


# ── Auth gate ─────────────────────────────────────────────────
if not is_logged_in():
    render_auth_page()
    st.stop()

user = get_current_user()
user_id = user["id"]

# ── Credentials gate ──────────────────────────────────────────
if not has_credentials(user_id):
    render_credentials_setup()
    st.stop()

# Load this user's credentials once per session
if "creds" not in st.session_state:
    st.session_state["creds"] = get_credentials(user_id)

creds = st.session_state["creds"]

# ── Header ────────────────────────────────────────────────────
st.markdown("<h1>🧠 AI Sprint Manager</h1>", unsafe_allow_html=True)
st.markdown('<p class="subtitle">Multi-agent system · PM → Dev → QA</p>', unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<div class="user-badge">👤 {user["email"]}</div>', unsafe_allow_html=True)
    if st.button("🚪 Log Out"):
        logout_user()
        st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Jira Settings")

    if "projects" not in st.session_state:
        with st.spinner("Loading projects..."):
            st.session_state["projects"] = get_jira_projects(creds=creds)

    projects = st.session_state["projects"]
    project_options = {f"{p['name']} ({p['key']})": p["key"] for p in projects}
    selected_project_label = st.selectbox("📁 Project", list(project_options.keys()))
    selected_project_key = project_options[selected_project_label]
    max_tickets = st.slider("Tickets to fetch", 1, 10, 3)

    if st.button("🔄 Fetch Tickets"):
        with st.spinner("Fetching tickets..."):
            tickets = get_jira_tickets(max_results=max_tickets, project_key=selected_project_key, creds=creds)
        st.session_state["tickets"] = tickets
        st.session_state["result"] = None
        st.success(f"✓ {len(tickets)} tickets from {selected_project_label}")

    st.markdown("---")
    st.markdown("### 🧠 Knowledge Base")

    if "confluence_spaces" not in st.session_state:
        with st.spinner("Loading spaces..."):
            st.session_state["confluence_spaces"] = get_confluence_spaces(creds=creds)

    conf_spaces = st.session_state["confluence_spaces"]
    space_options = {f"{s['name']} ({s['key']})": s["key"] for s in conf_spaces}

    selected_space_labels = st.multiselect(
        "📚 Confluence Spaces",
        options=list(space_options.keys()),
        default=list(space_options.keys())
    )
    selected_space_keys = [space_options[l] for l in selected_space_labels]
    st.session_state["selected_space_keys"] = selected_space_keys

    if st.button("🔄 Sync Knowledge Base"):
        with st.spinner("Indexing Confluence pages..."):
            count = index_confluence_pages(
                space_keys=selected_space_keys,
                creds=creds,
                user_id=user_id
            )
        st.success(f"✅ Indexed {count} pages")

    st.markdown("---")
    if st.button("🔧 Update Jira Credentials"):
        import sqlite3
        conn = sqlite3.connect("users.db")
        conn.execute("DELETE FROM user_credentials WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        st.session_state.pop("creds", None)
        st.rerun()


# ── Tabs ──────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🎯 Ticket Analysis", "💬 Chat"])

with tab1:
    if "tickets" not in st.session_state:
        st.markdown("""
        <div style="text-align:center; padding: 4rem 2rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">⬅️</div>
            <div style="font-size: 1rem; font-weight: 500; color: #6b7280;">Fetch tickets from Jira to get started</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        tickets = st.session_state["tickets"]
        options = [f"{t['id']} — {t['summary']}" for t in tickets]
        selected = st.selectbox("Select a ticket", options, label_visibility="collapsed")
        idx = [t["id"] for t in tickets].index(selected.split(" — ")[0])
        ticket = tickets[idx]

        st.markdown(f"""
        <div class="ticket-card">
            <div class="ticket-id">{ticket['id']} · {ticket['status']} · Jira Priority: {ticket['priority']}</div>
            <div class="ticket-title">{ticket['summary']}</div>
            <div class="ticket-desc">{ticket['description']}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚀 Run AI Analysis"):
            with st.spinner("Agents are thinking..."):
                result = run_pipeline(
                    ticket,
                    space_keys=st.session_state.get("selected_space_keys"),
                    creds=creds,
                    user_id=user_id
                )
                st.session_state["result"] = result

        if "result" in st.session_state and st.session_state["result"] is not None:
            result = st.session_state["result"]

            if not hasattr(result, 'tasks_output') or result.tasks_output is None:
                st.error("⚠️ Pipeline failed. Try running the analysis again.")
            else:
                outputs = result.tasks_output
                pm_data = parse_json_from_output(outputs[0])
                dev_data = parse_json_from_output(outputs[1])
                qa_data = parse_json_from_output(outputs[2])

                if pm_data:
                    priority = pm_data.get("priority", "P?")
                    reason = pm_data.get("reason", "")
                    p_class = get_priority_class(priority)
                    st.markdown(f"""
                    <div class="section-card" style="margin: 1rem 0;">
                        <div class="section-title">📋 PM Decision</div>
                        <span class="priority-badge {p_class}">{priority} — AI Assigned</span>
                        <div class="reason-text">{reason}</div>
                    </div>
                    """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)

                with col1:
                    if dev_data:
                        tasks = dev_data.get("tasks", [])
                        tasks_html = ""
                        for i, task in enumerate(tasks):
                            if isinstance(task, dict):
                                label = task.get("task", task.get("description", str(task)))
                            else:
                                label = str(task)
                            tasks_html += f'<div class="task-item"><div class="task-num">{i+1}</div><div>{label}</div></div>'
                        st.markdown(f"""
                        <div class="section-card">
                            <div class="section-title">🛠️ Dev Tasks · {len(tasks)} steps</div>
                            {tasks_html}
                        </div>
                        """, unsafe_allow_html=True)

                with col2:
                    if qa_data:
                        test_cases = qa_data.get("test_cases", [])
                        risks = qa_data.get("risks", [])

                        cases_html = ""
                        for case in test_cases:
                            desc = case.get("description", "") if isinstance(case, dict) else str(case)
                            result_text = case.get("expected_result", "") if isinstance(case, dict) else ""
                            cases_html += f'<div class="test-case"><div class="test-case-desc">✓ {desc}</div><div class="test-case-result">{result_text}</div></div>'

                        risks_html = ""
                        for risk in risks:
                            desc = risk.get("description", "") if isinstance(risk, dict) else str(risk)
                            mitigation = risk.get("mitigation", "") if isinstance(risk, dict) else ""
                            risks_html += f'<div class="risk-item"><div class="risk-desc">⚠ {desc}</div><div class="risk-mitigation">→ {mitigation}</div></div>'

                        st.markdown(f"""
                        <div class="section-card">
                            <div class="section-title">✅ Test Cases · {len(test_cases)} cases</div>
                            {cases_html}
                            <div class="section-title" style="margin-top:1.5rem;">🔴 Risks · {len(risks)} identified</div>
                            {risks_html}
                        </div>
                        """, unsafe_allow_html=True)

with tab2:
    st.markdown("### 💬 Chat with your Jira & Confluence data")
    st.caption("Ask anything about your tickets, projects, or documentation.")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    suggestions = [
        "What are the highest priority tickets?",
        "Summarize the payment architecture",
        "What are the known Safari issues?",
        "What is the dark mode feature spec?"
    ]
    st.markdown("**Try asking:**")
    cols = st.columns(4)
    for i, suggestion in enumerate(suggestions):
        with cols[i]:
            if st.button(suggestion, key=f"suggest_{i}"):
                st.session_state["pending_question"] = suggestion

    st.markdown("---")

    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="chat-message chat-user">
                <div class="chat-label" style="color:#6366f1">You</div>
                {msg["content"]}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message chat-assistant">
                <div class="chat-label" style="color:#10b981">AI Assistant</div>
                {msg["content"]}
            </div>
            """, unsafe_allow_html=True)

    question = st.chat_input("Ask about your projects, tickets, or docs...")

    if "pending_question" in st.session_state:
        question = st.session_state.pop("pending_question")

    if question:
        st.session_state["chat_history"].append({"role": "user", "content": question})
        with st.spinner("Thinking..."):
            answer = chat(
                question,
                space_keys=st.session_state.get("selected_space_keys"),
                project_keys=[selected_project_key],
                creds=creds,
                user_id=user_id
            )
        st.session_state["chat_history"].append({"role": "assistant", "content": answer})
        st.rerun()
