#!/usr/bin/env python3
"""CLI entry point for NarrateTTS."""
import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))


def run_server():
    """Start the web server."""
    import uvicorn
    from app.config import HOST, PORT

    print(f"Starting server on http://{HOST}:{PORT}")
    uvicorn.run("app.main:app", host=HOST, port=PORT)


def main():
    parser = argparse.ArgumentParser(description="NarrateTTS — Local text-to-speech")
    subparsers = parser.add_subparsers(dest="command")

    # run command (default)
    subparsers.add_parser("run", help="Start the web server")

    args = parser.parse_args()

    if args.command == "run":
        run_server()
    else:
        run_server()


if __name__ == "__main__":
    main()
