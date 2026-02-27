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
        """
        Execute a system command and capture its output.
        
        Parameters:
            cmd (List[str]): The command and its arguments to run.
            cwd (Optional[str]): Working directory in which to execute the command.
            check (bool): If True, raise subprocess.CalledProcessError when the process exits with a non-zero status.
        
        Returns:
            CommandResult: Captured `stdout`, `stderr`, and the process `returncode`.
        """


class SubprocessCommandRunner(CommandRunner):
    """Concrete command runner using subprocess."""

    def run(
        self, cmd: List[str], cwd: Optional[str] = None, check: bool = True
    ) -> CommandResult:
        """
        Execute a command and capture its stdout, stderr, and exit code.
        
        Parameters:
        	cmd (List[str]): Command and its arguments as a list of strings.
        	cwd (Optional[str]): Working directory to run the command in; if None, uses the current working directory.
        	check (bool): If True, a non-zero exit status will raise subprocess.CalledProcessError.
        
        Returns:
        	CommandResult: Immutable holder with `stdout`, `stderr`, and `returncode` from the executed command.
        """
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
        """
        Initialize the DockerComposeManager with the path to a Docker Compose directory and a command runner.
        
        Parameters:
            compose_dir (Path): Directory containing the Docker Compose configuration used when running compose commands.
            runner (CommandRunner): Executor responsible for running shell commands (e.g., docker compose).
        """
        self.compose_dir = compose_dir
        self.runner = runner

    def up(self) -> None:
        """
        Bring up Docker Compose services for the configured compose directory.
        
        Raises:
            subprocess.CalledProcessError: If `docker compose up` fails for reasons other than services already running.
        """
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
        """
        Waits until Redis at redis_cfg.url responds to a PING.
        
        Parameters:
            redis_cfg: An object with a `url` attribute pointing to the Redis server.
        
        Raises:
            RuntimeError: If Redis does not respond within 30 attempts (~30 seconds).
        """
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
        """
        Waits until the PostgreSQL server identified by db_cfg accepts a connection or raises on timeout.
        
        Attempts to connect up to 30 times with a 1-second pause between attempts. If a connection is established the function returns; if all attempts fail a RuntimeError is raised.
        
        Parameters:
            db_cfg: An object with a `dsn` attribute (connection DSN string) used by psycopg2.connect.
        
        Raises:
            RuntimeError: If PostgreSQL does not accept connections within the retry window.
        """
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
        """
        Create a DatabaseManager configured to operate against the target PostgreSQL instance.
        
        Parameters:
            db_cfg: Database connection configuration—either a DSN/connection string or a mapping of connection parameters used to connect to the PostgreSQL server.
        """
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
        """
        Initialize the manager with a command-runner dependency.
        
        Parameters:
            runner (CommandRunner): Command runner used to execute external shell commands for this manager.
        """
        self.runner = runner

    def obtain_and_save_token(self) -> None:
        """
        Execute the project's OAuth flow, extract the `access_token` from the flow's JSON output, and persist it to the ENV_FILE under the `UPSTOX_ACCESS_TOKEN` key.
        
        The function runs the auth flow process, parses its stdout as JSON for the `access_token`, and writes that token into the repository .env file. It logs progress and propagates any parsing or persistence errors.
        """
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
        """
        Initialize the manager with a command-runner dependency.
        
        Parameters:
            runner (CommandRunner): Command runner used to execute external shell commands for this manager.
        """
        self.runner = runner

    def load_catalog(self) -> None:
        """
        Ensure the local instrument catalog is present by running the catalog service and falling back to fetching from Upstox if needed.
        
        Attempts to run the catalog service module (which may upsert instruments). If the expected local catalog file does not exist after that step, downloads the catalog from Upstox and writes it to CATALOG_PATH.
        """
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
        """
        Start each ServiceConfig as a background process, creating or appending to the configured logfile.
        
        For each service, if its logfile exists and was modified within the last 10 seconds the service is considered already running and will be skipped; otherwise the service command is started with stdout and stderr redirected to the logfile.
        
        Parameters:
            services (List[ServiceConfig]): Service specifications to launch.
        """


class BackgroundServiceLauncher(ServiceLauncher):
    """Launches services in background with log files."""

    def launch(self, services: List[ServiceConfig]) -> None:
        """
        Start each service from `services` as a background process and record its stdout/stderr to the service's logfile.
        
        For each ServiceConfig, if the logfile exists and was modified within the last 10 seconds the service is treated as already running and is skipped; otherwise the function opens/creates the logfile and launches the configured command with stdout/stderr redirected to that file. New background processes are started with no monitoring by this function.
        
        Parameters:
            services (List[ServiceConfig]): List of service specifications to launch, each containing the command, logfile path, and name.
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


# --- Factory for Managers --------------------------------------------------
class ManagerFactory:
    """Factory to create manager instances."""

    @staticmethod
    def create_docker_manager(
        compose_dir: Path, runner: CommandRunner
    ) -> DockerComposeManager:
        """
        Create a DockerComposeManager configured for the given Docker Compose directory.
        
        Parameters:
            compose_dir (Path): Filesystem path containing the Docker Compose configuration.
        
        Returns:
            DockerComposeManager: Manager instance configured to operate on `compose_dir` using the provided command runner.
        """
        return DockerComposeManager(compose_dir, runner)

    @staticmethod
    def create_db_manager(db_cfg, runner: CommandRunner) -> DatabaseManager:
        """
        Create a DatabaseManager configured with the provided database settings.
        
        Parameters:
            db_cfg: Database configuration (e.g., a connection URL string or a config object) used to connect to the target PostgreSQL instance.
        
        Returns:
            DatabaseManager: An instance configured to manage schema and migrations for the specified database.
        """
        return DatabaseManager(db_cfg, runner)

    @staticmethod
    def create_oauth_manager(runner: CommandRunner) -> OAuthManager:
        """
        Create an OAuthManager configured to use the provided command runner.
        
        Parameters:
            runner (CommandRunner): Command execution helper used by the manager.
        
        Returns:
            OAuthManager: A new OAuthManager instance that uses the given runner.
        """
        return OAuthManager(runner)

    @staticmethod
    def create_catalog_manager(runner: CommandRunner) -> CatalogManager:
        """
        Create a CatalogManager configured with the given command runner.
        
        Returns:
            CatalogManager: An instance configured to use the provided CommandRunner for executing catalog-related commands.
        """
        return CatalogManager(runner)


# --- Command Pattern for Setup Steps ----------------------------------------
class SetupStep(ABC):
    """Base class for a setup step."""

    @abstractmethod
    def execute(self) -> None:
        """Execute the step."""


class StartInfraStep(SetupStep):
    def __init__(self, docker_manager: DockerComposeManager) -> None:
        """
        Create a StartInfraStep that will start infrastructure using the provided DockerComposeManager.
        
        Parameters:
            docker_manager (DockerComposeManager): Manager responsible for bringing up Docker Compose services.
        """
        self.docker_manager = docker_manager

    def execute(self) -> None:
        """
        Bring up the project's Docker Compose infrastructure.
        """
        self.docker_manager.up()


class HealthCheckStep(SetupStep):
    def __init__(self, redis_cfg, db_cfg) -> None:
        """
        Initialize the HealthCheckStep with configuration for Redis and PostgreSQL.
        
        Parameters:
            redis_cfg: Redis connection configuration or URL used by the health checker to create a Redis client and perform pings.
            db_cfg: PostgreSQL connection configuration (DSN string or mapping) used to establish database connections for readiness checks.
        """
        self.redis_cfg = redis_cfg
        self.db_cfg = db_cfg

    def execute(self) -> None:
        """
        Waits for Redis and PostgreSQL to become ready before proceeding.
        
        Calls the health checker to poll Redis and PostgreSQL using the step's configured connection settings; raises an error if either service does not become ready within the checker’s retry window.
        
        Raises:
            RuntimeError: If Redis or PostgreSQL fail to become ready within the allowed retries.
        """
        HealthChecker.wait_for_redis(self.redis_cfg)
        HealthChecker.wait_for_postgres(self.db_cfg)


class ApplySchemaStep(SetupStep):
    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Create an ApplySchemaStep bound to a DatabaseManager.
        
        Parameters:
            db_manager (DatabaseManager): Manager responsible for checking and applying the database schema.
        """
        self.db_manager = db_manager

    def execute(self) -> None:
        """
        Ensure the initial database schema is applied if missing.
        
        If the required tables are not present in the configured database, apply the project's initial schema.
        """
        self.db_manager.apply_schema_if_needed()


class OAuthStep(SetupStep):
    def __init__(self, oauth_manager: OAuthManager) -> None:
        """
        Initialize the OAuthStep with an OAuth manager.
        
        Parameters:
            oauth_manager (OAuthManager): Manager responsible for performing the OAuth flow and saving the retrieved token.
        """
        self.oauth_manager = oauth_manager

    def execute(self) -> None:
        """
        Ensures an Upstox access token is present in the environment, obtaining and saving one if missing.
        
        If the UPSTOX_ACCESS_TOKEN environment variable is not set, invokes the OAuth manager to obtain and persist a token; if the variable is already present, no action is taken.
        """
        if not os.getenv("UPSTOX_ACCESS_TOKEN"):
            self.oauth_manager.obtain_and_save_token()
        else:
            logger.info("Access token already present in environment")


class CatalogStep(SetupStep):
    def __init__(self, catalog_manager: CatalogManager) -> None:
        """
        Initialize the CatalogStep with a CatalogManager.
        
        Parameters:
            catalog_manager (CatalogManager): Manager responsible for loading or fetching the instrument catalog; stored for use by execute().
        """
        self.catalog_manager = catalog_manager

    def execute(self) -> None:
        """
        Ensure the instrument catalog is present and loaded.
        
        If the catalog file is missing, fetches and persists the catalog; otherwise leaves the existing catalog in place.
        """
        self.catalog_manager.load_catalog()


class LaunchServicesStep(SetupStep):
    def __init__(
        self, launcher: ServiceLauncher, services: List[ServiceConfig]
    ) -> None:
        """
        Initialize the LaunchServicesStep with a service launcher and the services to start.
        
        Parameters:
            launcher: ServiceLauncher used to start the configured services.
            services: List[ServiceConfig] describing each background service to launch.
        """
        self.launcher = launcher
        self.services = services

    def execute(self) -> None:
        """
        Launch the configured background services and log their access URLs and log filenames.
        
        Delegates service startup to the configured ServiceLauncher and records where the UI, API, and service logs can be found.
        """
        self.launcher.launch(self.services)
        logger.info("Services launched. UI will be available at http://localhost:8501")
        logger.info("API at http://localhost:8000")
        logger.info("Logs: streamer.log, ui-backend.log, ui-frontend.log")


# --- Orchestrator (Invoker) -----------------------------------------------
class SetupOrchestrator:
    """Orchestrates setup steps."""

    def __init__(self, steps: List[SetupStep]) -> None:
        """
        Constructs a SetupOrchestrator with an ordered list of setup steps.
        
        Parameters:
            steps (List[SetupStep]): Ordered list of setup steps that will be executed sequentially by run().
        """
        self.steps = steps

    def run(self) -> None:
        """Execute all steps."""
        logger.info("=== MarketMonitor One‑Click Setup ===")
        for step in self.steps:
            step.execute()
        logger.info("=== Done ===")


# --- Main --------------------------------------------------------------------
def main() -> None:
    """
    Wire up managers and setup steps, then run the orchestrator to prepare the system and optionally launch background services.
    
    Creates a subprocess command runner and manager instances for Docker, database, OAuth, and catalog, assembles the core setup steps (start infrastructure, health checks, apply schema, obtain OAuth token, load catalog), appends a launch-services step when invoked with the `--services` flag, and executes the SetupOrchestrator.
    """
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
