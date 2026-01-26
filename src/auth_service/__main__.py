"""Package entrypoint so ``python -m auth_service`` runs the CLI."""

from .cli import main

if __name__ == "__main__":
    main()
