from crewai import Crew, Process
from agents import pm_agent, dev_agent, qa_agent
from tasks import create_tasks

def run_pipeline(ticket, space_keys=None, creds=None, user_id=None):
    try:
        tasks = create_tasks(ticket, space_keys=space_keys, creds=creds, user_id=user_id)
        crew = Crew(
            agents=[pm_agent, dev_agent, qa_agent],
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
        result = crew.kickoff()
        return result
    except Exception as e:
        print(f"Pipeline error: {e}")
        return None
