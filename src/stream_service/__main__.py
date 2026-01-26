"""Package entrypoint so ``python -m stream_service`` runs the CLI."""

from .presentation.cli import main

if __name__ == "__main__":
    main()
