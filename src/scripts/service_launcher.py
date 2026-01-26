#!/usr/bin/env python3
"""Service launcher using Strategy pattern and OOP."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List

from src.common.logging import configure_logging

logger = configure_logging(__name__)


@dataclass(frozen=True)
class ServiceConfig:
    """Configuration for a background service."""

    cmd: List[str]
    logfile: str
    name: str


class ServiceLauncher(ABC):
    """Abstract strategy for launching services."""

    @abstractmethod
    def launch(self, services: List[ServiceConfig]) -> None:
        """Launch the given services."""


class BackgroundServiceLauncher(ServiceLauncher):
    """Launches services in background with log files."""

    def launch(self, services: List[ServiceConfig]) -> None:
        logger.info("Launching services (background processes)")
        for svc in services:
            if Path(svc.logfile).exists():
                try:
                    if time.time() - Path(svc.logfile).stat().st_mtime < 10:
                        logger.info(
                            "Service %s appears to be running (recent log), skipping",
                            svc.name,
                        )
                        continue
                except Exception:
                    pass
            with open(svc.logfile, "w", encoding="utf-8") as f:
                subprocess.Popen(svc.cmd, stdout=f, stderr=f)
            logger.info("Started %s (log: %s)", svc.name, svc.logfile)


class ServiceFactory:
    """Factory to create service configurations."""

    @staticmethod
    def create_marketmonitor_services() -> List[ServiceConfig]:
        catalog_path = Path("../../complete_data_formatted.json")
        return [
            ServiceConfig(
                cmd=[
                    sys.executable,
                    "-m",
                    "stream_service",
                    "--catalog",
                    str(catalog_path),
                ],
                logfile="../../streamer.log",
                name="streamer",
            ),
            ServiceConfig(
                cmd=[sys.executable, "-m", "ui.backend"],
                logfile="../../ui-backend.log",
                name="ui-backend",
            ),
            ServiceConfig(
                cmd=["streamlit", "run", "src/ui/frontend/app.py"],
                logfile="../../ui-frontend.log",
                name="ui-frontend",
            ),
        ]


def main() -> None:
    launcher = BackgroundServiceLauncher()
    services = ServiceFactory.create_marketmonitor_services()
    launcher.launch(services)
    logger.info("Services are running. UI at http://localhost:8501")
    logger.info("API at http://localhost:8000")


if __name__ == "__main__":
    main()
