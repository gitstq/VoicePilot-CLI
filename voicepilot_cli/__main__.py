"""
VoicePilot-CLI entry point.

Allows running the CLI via: python -m voicepilot_cli
"""

import sys

from voicepilot_cli.cli import main

if __name__ == "__main__":
    sys.exit(main())
