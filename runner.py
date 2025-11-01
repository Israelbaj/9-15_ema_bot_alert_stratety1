# runner.py
"""
Orchestrator script to run main then post_analysis (or resume where left off).
It uses run_state.json to resume safely and obeys runtime & API limits.
"""
import sys
import time
import json
from utils import load_run_state, save_run_state
from config import RUNTIME_LIMIT_MINUTES
from datetime import datetime, timezone

def run_once():
    state = load_run_state() or {}
    phase = state.get("phase", "main")

    print(f"Runner start: {datetime.now(timezone.utc).isoformat()} phase={phase}")

    # Engine: run main.py then post_analysis.py in order,
    # but respect the saved phase to resume.
    if phase == "main":
        import main
        main.main()
        # after main completes (or saves state) runner will re-load state
        state = load_run_state() or {}
        phase = state.get("phase", "post")
    if phase == "post":
        import post_analysis
        post_analysis.analyze_pending()
        # after post analysis we finish
    print("Runner finished.")

if __name__ == "__main__":
    run_once()
