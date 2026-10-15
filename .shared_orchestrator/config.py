"""Configuration and secrets management for the multi-agent orchestrator.

Loads runtime credentials, manages model role assignments (DeepSeek for coding,
OpenAI for orchestration/review/product), and provides secure environment forwarding
for Docker containers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Automatically load .env from the agentic root repository
_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env")


@dataclass
class RoleModelConfig:
    provider: str
    model: str


@dataclass
class OrchestratorConfig:
    # API Keys
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    deepseek_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY")
    )
    deepseek_base_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    anthropic_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )
    gemini_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )

    # Role Model Assignments
    orchestrator: RoleModelConfig = field(
        default_factory=lambda: RoleModelConfig(
            provider=os.getenv("ROLE_ORCHESTRATOR_PROVIDER", "openai"),
            model=os.getenv("ROLE_ORCHESTRATOR_MODEL", "gpt-4o"),
        )
    )
    planner: RoleModelConfig = field(
        default_factory=lambda: RoleModelConfig(
            provider=os.getenv("ROLE_PLANNER_PROVIDER", "openai"),
            model=os.getenv("ROLE_PLANNER_MODEL", "gpt-4o"),
        )
    )
    product: RoleModelConfig = field(
        default_factory=lambda: RoleModelConfig(
            provider=os.getenv("ROLE_PRODUCT_PROVIDER", "openai"),
            model=os.getenv("ROLE_PRODUCT_MODEL", "gpt-4o"),
        )
    )
    reviewer: RoleModelConfig = field(
        default_factory=lambda: RoleModelConfig(
            provider=os.getenv("ROLE_REVIEWER_PROVIDER", "openai"),
            model=os.getenv("ROLE_REVIEWER_MODEL", "gpt-4o"),
        )
    )
    coder: RoleModelConfig = field(
        default_factory=lambda: RoleModelConfig(
            provider=os.getenv("ROLE_CODER_PROVIDER", "deepseek"),
            model=os.getenv("ROLE_CODER_MODEL", "deepseek-chat"),
        )
    )

    docker_default_timeout: int = field(
        default_factory=lambda: int(os.getenv("DOCKER_DEFAULT_TIMEOUT", "300"))
    )

    def get_role_config(self, role_name: str) -> RoleModelConfig:
        """Lookup model configuration by role name."""
        mapping = {
            "orchestrator": self.orchestrator,
            "planner": self.planner,
            "product": self.product,
            "reviewer": self.reviewer,
            "coder": self.coder,
            "code_writer": self.coder,
        }
        if role_name not in mapping:
            raise KeyError(f"Unknown role '{role_name}'. Available: {list(mapping.keys())}")
        return mapping[role_name]

    def validate_keys(self, roles: Optional[List[str]] = None) -> Dict[str, bool]:
        """Validate whether keys are present for requested roles.
        
        Returns a dictionary of role -> status.
        """
        target_roles = roles or ["orchestrator", "planner", "reviewer", "coder"]
        results = {}
        for role in target_roles:
            role_cfg = self.get_role_config(role)
            provider = role_cfg.provider.lower()
            if provider == "openai":
                has_key = bool(self.openai_api_key and not self.openai_api_key.startswith("sk-placeholder"))
            elif provider == "deepseek":
                has_key = bool(self.deepseek_api_key and not self.deepseek_api_key.startswith("sk-placeholder"))
            elif provider == "anthropic":
                has_key = bool(self.anthropic_api_key)
            elif provider == "gemini":
                has_key = bool(self.gemini_api_key)
            else:
                has_key = False
            results[role] = has_key
        return results

    def get_docker_env_args(self, forward_keys: Optional[List[str]] = None) -> List[str]:
        """Generate CLI arguments for 'docker run' to forward credentials securely.
        
        Secrets are passed via environment variables directly at runtime,
        ensuring they are never baked into image layers or persisted.
        """
        keys = forward_keys or [
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "DEEPSEEK_BASE_URL",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
        ]
        args: List[str] = []
        for key in keys:
            val = os.getenv(key)
            if val is not None:
                args.extend(["-e", f"{key}={val}"])
        return args

    def get_docker_env_dict(self, forward_keys: Optional[List[str]] = None) -> Dict[str, str]:
        """Generate environment dictionary for Docker SDK or subprocess execution."""
        keys = forward_keys or [
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "DEEPSEEK_BASE_URL",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
        ]
        env_dict: Dict[str, str] = {}
        for key in keys:
            val = os.getenv(key)
            if val is not None:
                env_dict[key] = val
        return env_dict


# Global default configuration instance
config = OrchestratorConfig()
