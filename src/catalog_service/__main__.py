"""Package entrypoint so ``python -m catalog_service`` runs the upstox loader by default."""

from .upstox_loader import main

if __name__ == "__main__":
    main()
