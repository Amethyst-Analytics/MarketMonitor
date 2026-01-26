#!/usr/bin/env python3
"""MarketMonitor onboarding script using OOP, SOLID, and design patterns."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import psycopg2
import redis
from dotenv import set_key

from src.common.config import (
    load_database_config,
    load_redis_config,
    load_stream_config,
)
from src.common.logging import configure_logging

logger = configure_logging(__name__)

ENV_FILE = Path("../.env")
CATALOG_PATH = Path("../complete_data_formatted.json")


# --- Data Transfer Objects -------------------------------------------------
@dataclass(frozen=True)
class CommandResult:
    """Result of a command execution."""

    stdout: str
    stderr: str
    returncode: int


@dataclass(frozen=True)
class ServiceConfig:
    """Configuration for a background service."""

    cmd: List[str]
    logfile: str
    name: str


# --- Interfaces ------------------------------------------------------------
class CommandRunner(ABC):
    """Interface for running shell commands."""

    @abstractmethod
    def run(
        self, cmd: List[str], cwd: Optional[str] = None, check: bool = True
    ) -> CommandResult:
        """Execute a command and return the result."""


class SubprocessCommandRunner(CommandRunner):
    """Concrete command runner using subprocess."""

    def run(
        self, cmd: List[str], cwd: Optional[str] = None, check: bool = True
    ) -> CommandResult:
        logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(
            cmd, cwd=cwd, check=check, capture_output=True, text=True
        )
        return CommandResult(
            stdout=result.stdout, stderr=result.stderr, returncode=result.returncode
        )


# --- Managers (Single Responsibility) --------------------------------------
class DockerComposeManager:
    """Manages Docker Compose lifecycle."""

    def __init__(self, compose_dir: Path, runner: CommandRunner) -> None:
        self.compose_dir = compose_dir
        self.runner = runner

    def up(self) -> None:
        """Start services."""
        logger.info("Starting Docker Compose services")
        try:
            self.runner.run(
                ["docker", "compose", "up", "-d"], cwd=str(self.compose_dir)
            )
        except subprocess.CalledProcessError as e:
            if "already in use" in e.stderr or "is already up" in e.stderr:
                logger.info("Docker Compose services already running")
            else:
                raise


class HealthChecker:
    """Health checks for external services."""

    @staticmethod
    def wait_for_redis(redis_cfg) -> None:
        """Ping Redis until it's up."""
        r = redis.from_url(redis_cfg.url)
        for i in range(30):
            try:
                r.ping()
                logger.info("Redis is up")
                return
            except Exception:
                logger.info("Waiting for Redis... (%d/30)", i + 1)
                time.sleep(1)
        raise RuntimeError("Redis did not start in time")

    @staticmethod
    def wait_for_postgres(db_cfg) -> None:
        """Try connecting to Postgres until it's up."""
        for i in range(30):
            try:
                conn = psycopg2.connect(db_cfg.dsn)
                conn.close()
                logger.info("PostgreSQL is up")
                return
            except Exception:
                logger.info("Waiting for PostgreSQL... (%d/30)", i + 1)
                time.sleep(1)
        raise RuntimeError("PostgreSQL did not start in time")


class DatabaseManager:
    """Manages database schema."""

    def __init__(self, db_cfg, runner: CommandRunner) -> None:
        self.db_cfg = db_cfg
        self.runner = runner

    def apply_schema_if_needed(self) -> None:
        """Apply the initial schema if the instruments table does not exist."""
        try:
            conn = psycopg2.connect(self.db_cfg.dsn)
            cur = conn.cursor()
            cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'instruments')"
            )
            exists = cur.fetchone()[0]
            if not exists:
                logger.info("Applying initial schema")
                conn.close()
                self.runner.run(
                    [
                        "psql",
                        "-U",
                        "postgres",
                        "-d",
                        "market_data",
                        "-f",
                        "../migrations/001_initial.sql",
                    ]
                )
            else:
                logger.info("Schema already applied")
            conn.close()
        except psycopg2.Error as e:
            logger.error("Database connection failed: %s", e)
            raise


class OAuthManager:
    """Manages OAuth token acquisition and storage."""

    def __init__(self, runner: CommandRunner) -> None:
        self.runner = runner

    def obtain_and_save_token(self) -> None:
        """Run OAuth flow and save the token to .env."""
        logger.info("Running OAuth flow")
        result = self.runner.run([sys.executable, "-m", "auth_service"])
        try:
            payload = json.loads(result.stdout)
            token = payload["access_token"]
            logger.info("Saving access_token to .env")
            set_key(str(ENV_FILE), "UPSTOX_ACCESS_TOKEN", token)
        except Exception as exc:
            logger.error("Failed to parse OAuth response: %s", exc)
            raise


class CatalogManager:
    """Manages instrument catalog loading."""

    def __init__(self, runner: CommandRunner) -> None:
        self.runner = runner

    def load_catalog(self) -> None:
        """Run catalog service to upsert instruments."""
        logger.info("Loading instrument catalog")
        try:
            self.runner.run([sys.executable, "-m", "catalog_service"])
        except subprocess.CalledProcessError as e:
            logger.warning(
                "Catalog service reported issues (may already be loaded): %s", e.stderr
            )
        if not CATALOG_PATH.exists():
            logger.info("Catalog file not found; fetching from Upstox")
            from src.catalog_service.upstox_loader import download_catalog

            data = download_catalog()
            CATALOG_PATH.write_text(json.dumps(data, indent=2))
            logger.info("Saved catalog to %s", CATALOG_PATH)
        else:
            logger.info("Catalog file already present locally")


# --- Strategy for Service Launch -------------------------------------------
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


# --- Factory for Managers --------------------------------------------------
class ManagerFactory:
    """Factory to create manager instances."""

    @staticmethod
    def create_docker_manager(
        compose_dir: Path, runner: CommandRunner
    ) -> DockerComposeManager:
        return DockerComposeManager(compose_dir, runner)

    @staticmethod
    def create_db_manager(db_cfg, runner: CommandRunner) -> DatabaseManager:
        return DatabaseManager(db_cfg, runner)

    @staticmethod
    def create_oauth_manager(runner: CommandRunner) -> OAuthManager:
        return OAuthManager(runner)

    @staticmethod
    def create_catalog_manager(runner: CommandRunner) -> CatalogManager:
        return CatalogManager(runner)


# --- Command Pattern for Setup Steps ----------------------------------------
class SetupStep(ABC):
    """Base class for a setup step."""

    @abstractmethod
    def execute(self) -> None:
        """Execute the step."""


class StartInfraStep(SetupStep):
    def __init__(self, docker_manager: DockerComposeManager) -> None:
        self.docker_manager = docker_manager

    def execute(self) -> None:
        self.docker_manager.up()


class HealthCheckStep(SetupStep):
    def __init__(self, redis_cfg, db_cfg) -> None:
        self.redis_cfg = redis_cfg
        self.db_cfg = db_cfg

    def execute(self) -> None:
        HealthChecker.wait_for_redis(self.redis_cfg)
        HealthChecker.wait_for_postgres(self.db_cfg)


class ApplySchemaStep(SetupStep):
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def execute(self) -> None:
        self.db_manager.apply_schema_if_needed()


class OAuthStep(SetupStep):
    def __init__(self, oauth_manager: OAuthManager) -> None:
        self.oauth_manager = oauth_manager

    def execute(self) -> None:
        if not os.getenv("UPSTOX_ACCESS_TOKEN"):
            self.oauth_manager.obtain_and_save_token()
        else:
            logger.info("Access token already present in environment")


class CatalogStep(SetupStep):
    def __init__(self, catalog_manager: CatalogManager) -> None:
        self.catalog_manager = catalog_manager

    def execute(self) -> None:
        self.catalog_manager.load_catalog()


class LaunchServicesStep(SetupStep):
    def __init__(
        self, launcher: ServiceLauncher, services: List[ServiceConfig]
    ) -> None:
        self.launcher = launcher
        self.services = services

    def execute(self) -> None:
        self.launcher.launch(self.services)
        logger.info("Services launched. UI will be available at http://localhost:8501")
        logger.info("API at http://localhost:8000")
        logger.info("Logs: streamer.log, ui-backend.log, ui-frontend.log")


# --- Orchestrator (Invoker) -----------------------------------------------
class SetupOrchestrator:
    """Orchestrates setup steps."""

    def __init__(self, steps: List[SetupStep]) -> None:
        self.steps = steps

    def run(self) -> None:
        """Execute all steps."""
        logger.info("=== MarketMonitor One‑Click Setup ===")
        for step in self.steps:
            step.execute()
        logger.info("=== Done ===")


# --- Main --------------------------------------------------------------------
def main() -> None:
    """Entry point."""
    # Infrastructure
    runner = SubprocessCommandRunner()
    compose_dir = Path("deployments/docker-compose")
    docker_manager = ManagerFactory.create_docker_manager(compose_dir, runner)
    db_cfg = load_database_config()
    redis_cfg = load_redis_config()
    db_manager = ManagerFactory.create_db_manager(db_cfg, runner)
    oauth_manager = ManagerFactory.create_oauth_manager(runner)
    catalog_manager = ManagerFactory.create_catalog_manager(runner)

    # Steps
    steps: List[SetupStep] = [
        StartInfraStep(docker_manager),
        HealthCheckStep(redis_cfg, db_cfg),
        ApplySchemaStep(db_manager),
        OAuthStep(oauth_manager),
        CatalogStep(catalog_manager),
    ]

    # Optional services
    if "--services" in sys.argv:
        services = [
            ServiceConfig(
                cmd=[
                    sys.executable,
                    "-m",
                    "stream_service",
                    "--catalog",
                    str(CATALOG_PATH),
                ],
                logfile="../streamer.log",
                name="streamer",
            ),
            ServiceConfig(
                cmd=[sys.executable, "-m", "ui.backend"],
                logfile="../ui-backend.log",
                name="ui-backend",
            ),
            ServiceConfig(
                cmd=["streamlit", "run", "src/ui/frontend/app.py"],
                logfile="../ui-frontend.log",
                name="ui-frontend",
            ),
        ]
        launcher = BackgroundServiceLauncher()
        steps.append(LaunchServicesStep(launcher, services))
    else:
        logger.info("Setup complete. To start services, run:")
        logger.info("  python run_market_monitor.py --services")

    orchestrator = SetupOrchestrator(steps)
    orchestrator.run()


if __name__ == "__main__":
    main()
