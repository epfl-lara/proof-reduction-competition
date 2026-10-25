"""Small CPU interpreter for one productive job's original host tools."""

import sys
from pathlib import Path


def main():
    from proof_eval.training.bootstrap import configure_imports

    configure_imports(Path(__file__).resolve().parents[3])
    from proof_eval.training.tool_broker import serve

    serve(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
