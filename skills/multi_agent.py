"""
ARVIS Multi-Agent Delegation Skill — Spawns specialized sub-agents to solve subtasks
"""

import uuid
from agent.brain import ArvisBrain
from agent.task_router import TaskRouter

# Map of roles to specialized system prompts
ROLE_PROMPTS = {
    "coder": (
        "You are a Senior Software Engineer agent. Write clean, bug-free, and elegant code. "
        "Use execute_code tool to test your code and ensure it is fully correct before giving the final answer. "
        "Return only the tested, completed code."
    ),
    "reviewer": (
        "You are a Critical Code Reviewer agent. Review the provided code for security holes, syntax errors, "
        "inefficiencies, and potential bugs. Run your analysis, use math or tools if needed, and point out any issues."
    ),
    "analyst": (
        "You are a Meticulous Data Analyst agent. Process information, calculate stats, search facts, "
        "and present data-driven analysis in structured markdown tables."
    ),
    "researcher": (
        "You are an Advanced Researcher agent. Use web search and browser reading tools to collect detailed, "
        "up-to-date facts about any topic, synthesize the findings, and list sources."
    )
}

def delegate_task(role: str, task: str) -> str:
    """Spawns a specialized sub-agent (brain instance) to execute a subtask and return its findings.

    Roles available: coder, reviewer, analyst, researcher.
    """
    role_clean = role.lower().strip()
    session_id = f"subagent_{role_clean}_{uuid.uuid4().hex[:4]}"
    
    print(f"[Multi-Agent]: Spawning virtual '{role_clean}' agent for subtask: '{task[:60]}...'")
    
    try:
        # Create dedicated task router for the sub-agent
        router = TaskRouter()
        brain = ArvisBrain(session_id=session_id, task_router=router)
        
        # Override the sub-agent's system prompt with specialized instruction
        specialized_prompt = ROLE_PROMPTS.get(
            role_clean, 
            f"You are a specialized AI assistant. Your role is: {role_clean}. Focus exclusively on the assigned subtask."
        )
        brain.system_instruction = brain.get_system_instruction() + "\n\nROLE INSTRUCTION:\n" + specialized_prompt
        
        # Execute ReAct loop synchronously
        final_reply = ""
        for update in brain.execute_react_loop(task):
            if update["type"] == "final_answer":
                final_reply = update["content"]
                break
            elif update["type"] == "error":
                final_reply = f"Error from sub-agent: {update['message']}"
                break
                
        if not final_reply:
            final_reply = "Sub-agent completed execution but did not return a final answer."
            
        print(f"[Multi-Agent]: Virtual '{role_clean}' agent completed subtask successfully.")
        return final_reply
        
    except Exception as e:
        return f"Error delegating task to virtual agent: {str(e)}"
