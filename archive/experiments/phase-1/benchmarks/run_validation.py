#!/usr/bin/env python3
"""
CutPilot — Validation Master Runner
Runs Agent 1 and Agent 2 validation pipelines and ensures all deliverables are updated.
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
AGENT1_SCRIPT = SCRIPTS_DIR / "agent1_transcript.py"
AGENT2_SCRIPT = SCRIPTS_DIR / "agent2_video_analysis.py"


def main():
    print("=================================================================")
    print("CutPilot — Agent 1 & Agent 2 Validation Task: Master Runner")
    print("=================================================================\n")
    
    # 1. Run Agent 1
    print(">>> [1/2] Executing Agent 1: Transcript Extraction Pipeline...")
    res1 = subprocess.run([sys.executable, str(AGENT1_SCRIPT)], check=True)
    if res1.returncode != 0:
        print("Agent 1 failed!")
        sys.exit(1)
        
    print("\n-----------------------------------------------------------------\n")
    
    # 2. Run Agent 2
    print(">>> [2/2] Executing Agent 2: Video Understanding Pipeline...")
    res2 = subprocess.run([sys.executable, str(AGENT2_SCRIPT)], check=True)
    if res2.returncode != 0:
        print("Agent 2 failed!")
        sys.exit(1)
        
    print("\n=================================================================")
    print("All validation pipelines completed successfully.")
    print("Artifacts generated in: phase-1/test-results/")
    print("=================================================================")


if __name__ == "__main__":
    main()
