# 🧠 AI Sprint Manager

A multi-agent AI system that connects to your Jira and Confluence to automatically triage tickets, break them into dev tasks, and generate QA test cases — powered by CrewAI and Groq.

---

## Features

- **PM Agent** — assigns priority (P0–P3) with reasoning
- **Dev Agent** — breaks tickets into concrete implementation steps
- **QA Agent** — generates test cases and identifies risks
- **RAG Chat** — ask questions about your tickets and Confluence docs
- **Multi-user auth** — each user connects their own Jira account; credentials stored encrypted

---

## Tech Stack

- [Streamlit](https://streamlit.io) — UI
- [CrewAI](https://crewai.com) — multi-agent orchestration
- [Groq](https://groq.com) — LLM inference (llama-3.3-70b-versatile)
- [ChromaDB](https://trychroma.com) — vector store for RAG
- [SentenceTransformers](https://sbert.net) — embeddings
- SQLite + [cryptography](https://cryptography.io) — user storage with encrypted credentials

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/ai-sprint-manager.git
cd ai-sprint-manager
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Then edit `.env` and fill in your values:

- **JIRA_URL / JIRA_EMAIL / JIRA_API_TOKEN** — your Atlassian credentials (used as local dev fallback)
- **ENCRYPTION_KEY** — generate one with:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- **GROQ_API_KEY** — get one free at [console.groq.com](https://console.groq.com)

### 5. Run the app

```bash
streamlit run app.py
```

---

## How It Works

```
User signs up → connects their Jira account → credentials stored encrypted in SQLite
      ↓
Fetch tickets from their Jira project
      ↓
Run AI Analysis: PM Agent → Dev Agent → QA Agent (sequential CrewAI pipeline)
      ↓
Optional: Sync Confluence spaces → indexed into their own ChromaDB namespace
      ↓
Chat with their data via RAG
```

---

## Project Structure

```
├── app.py                  # Main Streamlit UI
├── auth.py                 # Login, signup, session management
├── database.py             # SQLite setup, user & credential storage
├── agents.py               # CrewAI agent definitions
├── tasks.py                # CrewAI task definitions
├── main.py                 # Pipeline runner with retry logic
├── chat_agent.py           # RAG-powered chat agent
├── jira_client.py          # Jira API client
├── confluence_client.py    # Confluence API client
├── rag.py                  # ChromaDB indexing and querying
├── .env.example            # Environment variable template
└── requirements.txt        # Python dependencies
```

---

## Notes on Rate Limits

This app uses Groq's free tier which has a **12,000 TPM limit**. If you hit a rate limit error, wait 20–30 seconds and try again. For production use, upgrade to Groq's Dev tier or swap the LLM in `agents.py`.

---

## Security

- User passwords are hashed with **bcrypt**
- Jira API tokens are **AES-encrypted** at rest using Fernet symmetric encryption
- The `ENCRYPTION_KEY`, `users.db`, and `chroma_db/` are all gitignored and never committed

---

## Contributing

Pull requests welcome. Please don't commit `.env` or `users.db`.
