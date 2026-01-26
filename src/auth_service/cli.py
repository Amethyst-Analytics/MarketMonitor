"""Command-line entry point for the Upstox OAuth helper."""

from __future__ import annotations

import argparse
import json

from src.common.config import load_upstox_config
from src.common.logging import configure_logging

from .oauth_client import OAuthClient


def main() -> None:
    """Execute the OAuth flow and print the resulting token payload."""

    parser = argparse.ArgumentParser(description="Upstox OAuth helper")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Print the authorization URL instead of auto-opening the browser.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Seconds to wait for the authorization callback (default: 180).",
    )
    args = parser.parse_args()

    logger = configure_logging(__name__)
    config = load_upstox_config()
    oauth_client = OAuthClient(config)

    try:
        token_payload = oauth_client.run_flow(
            timeout=args.timeout, open_browser=not args.no_browser
        )
    except Exception as exc:  # noqa: BLE001 - user-facing CLI
        logger.error("OAuth flow failed: %s", exc)
        raise SystemExit(1) from exc

    print(json.dumps(token_payload, indent=2))
    logger.info(
        "Store the access_token in UPSTOX_ACCESS_TOKEN for downstream services."
    )


if __name__ == "__main__":
    main()
