"""Run the whole pipeline in order: generate → load → clean → match → analyse."""

import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
STEPS = ["generate_data.py", "load_to_db.py", "clean.py", "match.py", "analyse.py"]


def main():
    for step in STEPS:
        print(f"\n=== {step} ===", flush=True)  # show the header before the step runs
        subprocess.run([sys.executable, str(SRC / step)], check=True)
    print("\nPipeline finished. Start the app with: streamlit run src/app.py")


if __name__ == "__main__":
    main()
