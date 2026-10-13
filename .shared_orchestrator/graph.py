import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

# 1. Define the shared state structure passed between nodes
class AgentState(TypedDict):
    user_request: str
    prd_output: str
    tasks: List[dict]
    current_task_index: int
    review_status: str
    logs: List[str]

workflow = StateGraph(AgentState)

# 2. Define Node Functions (using your model router for cost optimization)
def product_strategy_node(state: AgentState):
    """Uses a frontier model + web search to build a PRD"""
    print("--- [Product Strategist] Researching market & drafting PRD ---")
    # Call Claude / GPT-4o with internet search tool enabled
    return {"prd_output": "PRD generated: Add OAuth login handler."}

def planner_node(state: AgentState):
    """Decomposes PRD into atomic tasks"""
    print("--- [Architect Planner] Breaking PRD into task JSON ---")
    # Call model to output structured task list
    mock_tasks = [{"id": "TASK-1", "file": "src/auth.ts", "instruction": "Add login validation"}]
    return {"tasks": mock_tasks, "current_task_index": 0}

def code_writer_node(state: AgentState):
    """Spins up ephemeral worktree & container running DeepSeek-V3"""
    task = state["tasks"][state["current_task_index"]]
    print(f"--- [Code Worker (DeepSeek)] Executing task: {task['id']} ---")
    # Orchestrator spins up git worktree, mounts container, runs DeepSeek
    return {"logs": [f"Executed {task['id']} with atomic commit"]}

def reviewer_node(state: AgentState):
    """Reviews diff against criteria"""
    print("--- [Code Reviewer] Evaluating git diff ---")
    return {"review_status": "APPROVED"}

# 3. Build the Graph Topology
workflow.add_node("product_strategist", product_strategy_node)
workflow.add_node("planner", planner_node)
workflow.add_node("code_writer", code_writer_node)
workflow.add_node("reviewer", reviewer_node)

workflow.set_entry_point("product_strategist")
workflow.add_edge("product_strategist", "planner")
workflow.add_edge("planner", "code_writer")
workflow.add_edge("code_writer", "reviewer")

# Conditional routing based on review outcome
def should_continue(state: AgentState):
    if state["review_status"] == "APPROVED":
        return END
    return "code_writer" # Loop back to fix if rejected

workflow.add_conditional_edges("reviewer", should_continue, {END: END, "code_writer": "code_writer"})

app = workflow.compile()