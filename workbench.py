"""Launch the local Python interface; native MATLAB files run independently."""
import importlib.util
from pathlib import Path
import subprocess
import sys


def main():
    if importlib.util.find_spec('streamlit') is None:
        print('Missing dependencies. Create .venv and install requirements.txt; see README.md.', file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parent
    command = [sys.executable, '-m', 'streamlit', 'run', str(root / 'app.py'), '--server.address', '127.0.0.1',
               '--browser.gatherUsageStats', 'false']
    try:
        return subprocess.call(command, cwd=root)
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    sys.exit(main())
