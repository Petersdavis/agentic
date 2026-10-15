# AGENTS.md — Agent Operations & Orchestration Guide

Welcome to the **Agentic** multi-project orchestrator repository. If you are an AI agent operating in this repository, read and follow these rules strictly.

---

## 🧭 Repository Map

| Path | Purpose | Ownership / Access |
|---|---|---|
| [`.shared_orchestrator/`](file:///home/pdavis/dev/agentic/.shared_orchestrator) | LangGraph-based workflow orchestrator | Orchestrator / Planner agents |
| [`.shared_orchestrator/graph.py`](file:///home/pdavis/dev/agentic/.shared_orchestrator/graph.py) | Master StateGraph definition | Orchestrator agents |
| [`.shared_orchestrator/roles/`](file:///home/pdavis/dev/agentic/.shared_orchestrator/roles) | Role prompts & constraints for worker/reviewer/planner agents | System definitions |
| [`projects/`](file:///home/pdavis/dev/agentic/projects) | Individual application repositories | Sub-project workspaces |
| [`projects/<name>/plan/progress.json`](file:///home/pdavis/dev/agentic/projects) | Master status ledger and roadmap for a project | Planner creates; **Workers only update `status`** |
| [`projects/<name>/plan/tasks/<id>.json`](file:///home/pdavis/dev/agentic/projects) | Localized per-task scratchpad and spec | Assigned worker agent owns read/write |
| [`docker/`](file:///home/pdavis/dev/agentic/docker) | Dockerfiles and container configurations for task isolation | Shared infrastructure |

---

## 🔒 Golden Rules of Engagement

### 1. 100% Serial Execution
Work on any project plan must proceed **top-to-bottom, strictly serially**. Do not attempt to run multiple tasks in parallel unless explicitly instructed. Always check:
- Is the preceding task `done`?
- Are all dependencies in `depends_on` marked `done`?

### 2. State & File Modification Boundaries
- **Single Source of Truth**: `projects/<name>/plan/progress.json` is authoritative for task status.
- **Worker agents may ONLY modify the `status` field in `progress.json`**. Do not add, delete, or reorder tasks, and do not modify requirements or context in `progress.json`.
- **Worker scratch space**: Use `projects/<name>/plan/tasks/<id>.json` for notes, progress updates, and intermediate findings.
- **Atomic file updates**: Always use a temporary file with `mv` when using `jq` to prevent file corruption.

### 3. Docker Containers & Ephemeral Git Workspaces
- All task development should occur inside isolated **Docker containers**.
- Each task operates in an ephemeral Git workspace (e.g., git worktree or isolated feature branch).
- Never leave untracked temporary files or dirty states in the main branch.
- Once a task passes review and is committed, clean up the ephemeral workspace.

### 4. Role Responsibilities
- **Planner / Orchestrator**: Traverses `progress.json`, selects the next pending unblocked task, provisions workspace, and triggers the worker.
- **Code Writer**: Reads the task specification in `tasks/<id>.json`, updates `status` to `in_progress`, modifies code within the `context` globs, executes validation tests, records notes, and requests review.
- **Reviewer / QA**: Inspects `git diff`, ensures acceptance criteria are satisfied, verifies tests pass, and marks `done` (or rejects with actionable feedback). Circuit breaker halts execution after 3 failed attempts.

---

## 🛠️ Tooling & Command Patterns (`jq`)

When reading and modifying plan files, use `jq` with safe temp files:

```bash
# 1. Find the next pending task in a project
jq -r '.tasks[] | select(.status == "pending") | .id' projects/<project>/plan/progress.json | head -n 1

# 2. Inspect a specific task
jq '.tasks[] | select(.id == "<task_id>")' projects/<project>/plan/progress.json

# 3. Update status to 'in_progress' (Worker rule: status field ONLY)
jq '(.tasks[] | select(.id == "<task_id>") | .status) = "in_progress"' \
  projects/<project>/plan/progress.json > /tmp/progress.json \
  && mv /tmp/progress.json projects/<project>/plan/progress.json

# 4. Update worker notes in the localized task scratch sheet
jq '.notes = "Completed implementation and validated tests."' \
  projects/<project>/plan/tasks/<task_id>.json > /tmp/task.json \
  && mv /tmp/task.json projects/<project>/plan/tasks/<task_id>.json

# 5. Mark task 'review' or 'done' in progress.json
jq '(.tasks[] | select(.id == "<task_id>") | .status) = "done"' \
  projects/<project>/plan/progress.json > /tmp/progress.json \
  && mv /tmp/progress.json projects/<project>/plan/progress.json
```

---

## ➕ Creating a Task

Only **Planner / Orchestrator** agents create tasks. Creating a task is a two-step operation: first append the task entry to the `.tasks[]` array in `progress.json`, then create the matching localized spec file at `projects/<project>/plan/tasks/<task_id>.json`.

### Step 1 — Append the task to `.tasks[]` in `progress.json`

Use `jq` with `+=` to append a new object to the `.tasks[]` array. Always write to a temp file and `mv` it back to keep the update atomic.

```bash
# Append a new task to the .tasks[] array (Planner only)
jq --arg id "<task_id>" \
   --arg title "<task title>" \
   --arg status "pending" \
   --argjson depends_on '[]' \
   --argjson context '["projects/<project>/**"]' \
   '.tasks += [{
      id: $id,
      title: $title,
      status: $status,
      depends_on: $depends_on,
      context: $context
    }]' \
  projects/<project>/plan/progress.json > /tmp/progress.json \
  && mv /tmp/progress.json projects/<project>/plan/progress.json
```

> **Note**: `--arg` passes strings, `--argjson` passes raw JSON (arrays, objects, numbers, booleans). Use `--argjson` for `depends_on` and `context` so they are stored as real arrays rather than strings.

### Step 2 — Read the appended task and create its spec file

After appending, read the newly added task back out of `progress.json` and write it to the localized task scratch sheet at `projects/<project>/plan/tasks/<task_id>.json`. This file is the assigned worker's read/write scratchpad.

```bash
# Read the appended task and write it to tasks/<task_id>.json
jq --arg id "<task_id>" \
   '.tasks[] | select(.id == $id)' \
  projects/<project>/plan/progress.json > /tmp/task.json \
  && mv /tmp/task.json projects/<project>/plan/tasks/<task_id>.json
```

### Step 3 — Verify the task was created

```bash
# Confirm the task exists in progress.json
jq '.tasks[] | select(.id == "<task_id>")' projects/<project>/plan/progress.json

# Confirm the localized spec file was written
cat projects/<project>/plan/tasks/<task_id>.json
```

### Task Creation Rules

- **Planner / Orchestrator only**: Worker agents must never append, delete, or reorder tasks. Workers may only modify the `status` field.
- **Unique `id`**: Each `<task_id>` must be unique within the project's `.tasks[]` array.
- **Valid `depends_on`**: Every id listed in `depends_on` must reference an existing task in the same project.
- **Ordering matters**: Tasks execute top-to-bottom, strictly serially. Append new tasks in the intended execution order.
- **Always create the spec file**: A task is not fully created until both the `.tasks[]` entry and the `tasks/<task_id>.json` file exist.
- **Atomic writes**: Always use the `/tmp` file + `mv` pattern to avoid corrupting `progress.json`.