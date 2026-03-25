from crewai import Agent

pm_agent = Agent(
    role="Product Manager",
    goal="Analyze Jira tickets and assign priority P0-P3 with clear reasoning",
    backstory="You are a senior PM who triages tickets by user impact, urgency, and dependencies.",
    llm="groq/llama-3.3-70b-versatile",
    verbose=True
)

dev_agent = Agent(
    role="Senior Developer",
    goal="Break down tickets into concrete, actionable development tasks",
    backstory="You are a senior engineer who turns requirements into clear implementation steps.",
    llm="groq/llama-3.3-70b-versatile",
    verbose=True
)

qa_agent = Agent(
    role="QA Engineer",
    goal="Write test cases and identify risks for each ticket",
    backstory="You are a QA lead who catches edge cases and writes thorough test scenarios.",
    llm="groq/llama-3.3-70b-versatile",
    verbose=True
)