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
        """
        Launch multiple services as background processes with their stdout/stderr redirected to each service's logfile.
        
        Each ServiceConfig in `services` will be checked; if its logfile was modified within the last 10 seconds the service is treated as already running and will be skipped (errors during this check are ignored). Services that are started will have their stdout and stderr written to the configured logfile, and the method logs progress for each service.
        
        Parameters:
        	services (List[ServiceConfig]): List of service configurations to launch.
        """


class BackgroundServiceLauncher(ServiceLauncher):
    """Launches services in background with log files."""

    def launch(self, services: List[ServiceConfig]) -> None:
        """
        Launch each ServiceConfig as a background process, redirecting stdout/stderr to its configured logfile.
        
        For each service, if the service's logfile exists and was modified within the last 10 seconds, the service is assumed to be running and is skipped. Errors encountered while checking logfile modification time are ignored; services are started by invoking their command with subprocess.Popen and truncating the logfile before launch.
        
        Parameters:
            services (List[ServiceConfig]): Services to start; each service's stdout and stderr are written to its `logfile`.
        """
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
        """
        Create predefined ServiceConfig objects for the Market Monitor services.
        
        The returned list contains three service configurations:
        - "streamer": runs the `stream_service` module with a catalog at "../../complete_data_formatted.json".
        - "ui-backend": runs the `ui.backend` module.
        - "ui-frontend": runs the Streamlit app at "src/ui/frontend/app.py".
        
        Returns:
            List[ServiceConfig]: A list of ServiceConfig instances for streamer, ui-backend, and ui-frontend.
        """
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
    """
    Launches the predefined market-monitoring background services and logs their UI and API endpoints.
    
    Creates a BackgroundServiceLauncher, obtains service configurations from ServiceFactory, starts the services, and emits informational logs with the UI and API URLs.
    """
    launcher = BackgroundServiceLauncher()
    services = ServiceFactory.create_marketmonitor_services()
    launcher.launch(services)
    logger.info("Services are running. UI at http://localhost:8501")
    logger.info("API at http://localhost:8000")


if __name__ == "__main__":
    main()
