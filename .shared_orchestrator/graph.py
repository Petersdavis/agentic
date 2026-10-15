import os
import json
import subprocess
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

PROGRESS_FILE = "progress.json"
TASKS_DIR = "tasks"

class AgentState(TypedDict):
    tasks: List[dict]
    current_task_id: str
    review_status: str
    attempt_count: int
    logs: List[str]

# --- Helper Utilities (Using jq as per AGENTS.md spec) ---

def run_jq_update_status(task_id: str, new_status: str):
    """Worker agents may ONLY modify the status field in progress.json via jq."""
    tmp_file = f"{PROGRESS_FILE}.tmp"
    cmd = (
        f"jq '(.tasks[] | select(.id == \"{task_id}\") | .status) = \"{new_status}\"' "
        f"{PROGRESS_FILE} > {tmp_file} && mv {tmp_file} {PROGRESS_FILE}"
    )
    subprocess.run(cmd, shell=True, check=True)

def update_task_scratch_notes(task_id: str, notes: str):
    """Worker agents own tasks/<id>.json and can freely write notes."""
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    if os.path.exists(task_file):
        tmp_file = f"{task_file}.tmp"
        # Safely update notes field using jq or python json handling
        with open(task_file, "r") as f:
            data = json.load(f)
        data["notes"] = notes
        with open(tmp_file, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_file, task_file)

# --- Node Definitions ---

def planner_node(state: AgentState):
    print("--- [Planner] Reading master task list from progress.json ---")
    if not os.path.exists(PROGRESS_FILE):
        raise FileNotFoundError("progress.json missing. Planner must initialize the plan.")
    
    with open(PROGRESS_FILE, "r") as f:
        data = json.load(f)
        tasks = data.get("tasks", [])

    # Find the first task that is pending or unblocked
    active_task_id = None
    for task in tasks:
        if task["status"] == "pending":
            active_task_id = task["id"]
            break

    return {"tasks": tasks, "current_task_id": active_task_id}

def code_writer_node(state: AgentState):
    task_id = state["current_task_id"]
    if not task_id:
        return {"logs": ["No active tasks to process."]}

    attempts = state.get("attempt_count", 0) + 1
    print(f"--- [Worker Agent] Starting task: {task_id} (Attempt {attempts}) ---")

    # 1. Update master progress.json status via strict jq rule
    run_jq_update_status(task_id, "in_progress")

    # 2. Read context glob / scratch file requirements
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    print(f"--- [Worker Agent] Reading localized scratch sheet: {task_file} ---")

    # Simulate code writing & localized scratch pad updates
    update_task_scratch_notes(task_id, f"Attempt {attempts}: Implemented feature code.")

    return {"attempt_count": attempts, "logs": [f"Executed {task_id}"]}

def reviewer_node(state: AgentState):
    task_id = state["current_task_id"]
    print(f"--- [Reviewer & Tester] Running tests and evaluating requirements for {task_id} ---")

    # Run deterministic tests (e.g., pytest / npm test) via subprocess here...
    tests_passed = True # Simulated outcome

    if tests_passed:
        # Mark as done in master progress.json using strict jq rule
        run_jq_update_status(task_id, "done")
        update_task_scratch_notes(task_id, "Requirements verified and passed.")
        
        return {
            "review_status": "APPROVED",
            "attempt_count": 0, # Reset for next task
            "current_task_id": "" 
        }
    else:
        run_jq_update_status(task_id, "blocked")
        return {"review_status": "REJECTED"}

# --- Graph Assembly ---

workflow = StateGraph(AgentState)

workflow.add_node("planner", planner_node)
workflow.add_node("code_writer", code_writer_node)
workflow.add_node("reviewer", reviewer_node)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "code_writer")
workflow.add_edge("code_writer", "reviewer")

def should_continue(state: AgentState):
    # If all tasks are completed or loop finished
    if not state.get("current_task_id"):
        return END
    
    # Circuit breaker: max 3 attempts per task
    if state.get("attempt_count", 0) >= 3:
        print(f"--- [Circuit Breaker] Max attempts reached for current task. Halting. ---")
        return END

    if state["review_status"] == "APPROVED":
        return "planner" # Go back to planner to pick up the next task
        
    return "code_writer" # Retry task implementation loop if rejected

workflow.add_conditional_edges("reviewer", should_continue, {END: END, "planner": "planner", "code_writer": "code_writer"})

app = workflow.compile()