import sys
from pathlib import Path

# Add .shared_orchestrator to sys.path for test discovery
orchestrator_path = str(Path(__file__).resolve().parent.parent / ".shared_orchestrator")
if orchestrator_path not in sys.path:
    sys.path.insert(0, orchestrator_path)
