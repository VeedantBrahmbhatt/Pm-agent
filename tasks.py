from crewai import Task
from agents import pm_agent, dev_agent, qa_agent
from rag import query_rag

def create_tasks(ticket, space_keys=None, creds=None, user_id=None):
    ticket_context = f"""
    Ticket ID: {ticket['id']}
    Summary: {ticket['summary']}
    Description: {ticket['description']}
    Current Priority: {ticket['priority']}
    Status: {ticket['status']}
    """

    rag_context = query_rag(
        f"{ticket['summary']} {ticket['description']}",
        space_keys=space_keys,
        user_id=user_id
    )
    context_block = f"\n\nRelevant project context from Confluence:\n{rag_context}" if rag_context else ""

    pm_task = Task(
        description=f"Analyze this Jira ticket and return a JSON with 'priority' (P0-P3) and 'reason'.\n{ticket_context}{context_block}",
        agent=pm_agent,
        expected_output="JSON with priority and reason fields"
    )
    dev_task = Task(
        description=f"Based on the PM analysis, return a JSON with 'tasks' as a list of dev steps.\n{ticket_context}{context_block}",
        agent=dev_agent,
        expected_output="JSON with a tasks array"
    )
    qa_task = Task(
        description=f"Based on the dev tasks, return a JSON with 'test_cases' and 'risks' arrays.\n{ticket_context}{context_block}",
        agent=qa_agent,
        expected_output="JSON with test_cases and risks arrays"
    )
    return [pm_task, dev_task, qa_task]
