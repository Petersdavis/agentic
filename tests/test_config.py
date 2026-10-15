import sys
from pathlib import Path

# Add .shared_orchestrator to sys.path so its modules can be imported directly
_orchestrator_dir = str(Path(__file__).resolve().parent.parent / ".shared_orchestrator")
if _orchestrator_dir not in sys.path:
    sys.path.insert(0, _orchestrator_dir)

import pytest
from config import OrchestratorConfig, RoleModelConfig


def test_role_model_assignments():
    cfg = OrchestratorConfig()
    
    # Coder should be assigned to DeepSeek
    coder_cfg = cfg.get_role_config("coder")
    assert coder_cfg.provider == "deepseek"
    assert coder_cfg.model == "deepseek-chat"
    
    # Orchestrator, Planner, Reviewer, Product should be assigned to OpenAI
    for role in ["orchestrator", "planner", "reviewer", "product"]:
        role_cfg = cfg.get_role_config(role)
        assert role_cfg.provider == "openai"
        assert role_cfg.model == "gpt-4o"


def test_docker_env_forwarding(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    
    cfg = OrchestratorConfig()
    env_args = cfg.get_docker_env_args()
    assert "-e" in env_args
    assert "OPENAI_API_KEY=test-openai-key" in env_args
    assert "DEEPSEEK_API_KEY=test-deepseek-key" in env_args
    assert "DEEPSEEK_BASE_URL=https://api.deepseek.com" in env_args
    
    env_dict = cfg.get_docker_env_dict()
    assert env_dict["OPENAI_API_KEY"] == "test-openai-key"
    assert env_dict["DEEPSEEK_API_KEY"] == "test-deepseek-key"


def test_key_validation(monkeypatch):
    # With placeholder keys
    monkeypatch.setenv("OPENAI_API_KEY", "sk-placeholder-openai-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-placeholder-deepseek-key")
    
    cfg = OrchestratorConfig(
        openai_api_key="sk-placeholder-openai-key",
        deepseek_api_key="sk-placeholder-deepseek-key"
    )
    val = cfg.validate_keys(["coder", "reviewer"])
    assert val["coder"] is False
    assert val["reviewer"] is False
    
    # With real-looking keys
    real_cfg = OrchestratorConfig(
        openai_api_key="sk-proj-valid-openai-key",
        deepseek_api_key="sk-valid-deepseek-key"
    )
    val_real = real_cfg.validate_keys(["coder", "reviewer"])
    assert val_real["coder"] is True
    assert val_real["reviewer"] is True
