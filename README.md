# Agentic

A PDM-managed Python project for building a LangGraph-based shared orchestrator.

## Setup

```bash
pdm install
```

## Packages

- `langchain-core`
- `langchain-anthropic`
- `langgraph`

## Usage

The LangGraph application lives in [`.shared_orchestrator/graph.py`](.shared_orchestrator/graph.py).

```bash
pdm run python -c "import sys; sys.path.insert(0, '.shared_orchestrator'); import graph; print(graph.app)"
```
