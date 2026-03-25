import os
from crewai import Agent, Task, Crew, Process
from jira_client import get_jira_tickets
from rag import query_rag
from dotenv import load_dotenv

load_dotenv()

chat_agent = Agent(
    role="Product Intelligence Assistant",
    goal="Answer questions about Jira tickets and Confluence documentation clearly and concisely",
    backstory="You are a helpful assistant with deep knowledge of the team's projects, tickets, and documentation. You answer questions based on real data provided to you.",
    llm="groq/llama-3.3-70b-versatile",
    verbose=False
)

def truncate(text, max_chars=800):
    return text[:max_chars] + "..." if len(text) > max_chars else text

def chat(question, space_keys=None, project_keys=None, creds=None, user_id=None):
    # RAG context from the user's own indexed Confluence
    rag_context = query_rag(question, space_keys=space_keys, n_results=3, user_id=user_id)

    # Jira context using the user's own credentials
    jira_context = ""
    try:
        keys = project_keys or []
        if keys:
            tickets = get_jira_tickets(max_results=5, project_key=keys[0], creds=creds)
            if tickets:
                ticket_lines = [
                    f"- [{t['id']}] {t['summary']} | Priority: {t['priority']} | Status: {t['status']}"
                    for t in tickets
                ]
                jira_context = "Current Jira Tickets:\n" + "\n".join(ticket_lines)
    except Exception as e:
        print(f"Jira context error: {e}")

    full_context = ""
    if rag_context:
        full_context += f"Confluence Documentation:\n{truncate(rag_context, 1500)}\n\n"
    if jira_context:
        full_context += truncate(jira_context, 800)

    task = Task(
        description=f"""Answer this question using the context provided below.
Be concise (3-5 sentences max). If the answer isn't in the context, say so clearly.

Question: {question}

Context:
{full_context}
""",
        agent=chat_agent,
        expected_output="A concise answer to the question in 3-5 sentences"
    )

    crew = Crew(
        agents=[chat_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False
    )

    try:
        result = crew.kickoff()
        return str(result)
    except Exception as e:
        return f"Error: {e}"
