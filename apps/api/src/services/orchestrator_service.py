import logging
import socket
import uuid

import docker

from apps.api.src.config.settings import settings

logger = logging.getLogger("unotusk-orchestrator")

class OrchestratorService:
    @staticmethod
    def _find_available_port(start_port: int = 28100, max_port: int = 28999) -> int:
        for port in range(start_port, max_port + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('0.0.0.0', port))
                    return port
                except OSError:
                    continue
        raise RuntimeError("No available ports in the specified range.")

    @staticmethod
    async def spawn_project_container(project_id: uuid.UUID, organization_id: uuid.UUID) -> int:
        """
        Spawns a Data Plane container for the given project.
        Shares the database and auth secrets but isolates compute.
        Returns the host port assigned to the project.
        """
        port = OrchestratorService._find_available_port()
        logger.info(f"Spawning Data Plane for Project {project_id} on port {port}...")

        try:
            client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to docker daemon: {e}")
            raise RuntimeError("Orchestration failed: Docker daemon not accessible.") from e

        container_name = f"unotusk-project-{str(project_id)[:8]}"

        # We reuse the same API image but without exposing control plane endpoints if we wanted to.
        # For MVP, we just spin up the API instance and tell it its PROJECT_ID.
        environment = {
            "APP_ENV": "production",
            "DEBUG": "false",
            "DATABASE_URL": settings.DATABASE_URL,
            "SYNC_DATABASE_URL": settings.SYNC_DATABASE_URL,
            "REDIS_URL": settings.REDIS_URL,
            "AUTH_SECRET": settings.AUTH_SECRET,
            "DATA_PLANE_PROJECT_ID": str(project_id),
            "DATA_PLANE_ORG_ID": str(organization_id),
        }

        try:
            # We assume the image `ghcr.io/techteam-zephvion/unotusk-api:v1.0.1` is used,
            # or `unotusk-api:0.1.0` if running locally.
            # We will use the same image as the current container running this code.
            # To find it, we can inspect our own container, or hardcode it for MVP.
            image_name = "unotusk-api:0.1.0"

            # Discover our own network if running inside docker
            hostname = socket.gethostname()
            network_name = "bridge"
            try:
                self_container = client.containers.get(hostname)
                networks = self_container.attrs.get("NetworkSettings", {}).get("Networks", {})
                if networks:
                    network_name = list(networks.keys())[0]
            except Exception:
                pass

            # Start the container
            container = client.containers.run(
                image_name,
                name=container_name,
                environment=environment,
                ports={'8000/tcp': port},
                detach=True,
                network=network_name,
                restart_policy={"Name": "always"}
            )
            logger.info(f"Successfully spawned container {container_name} (ID: {container.short_id}) on port {port}.")
            return port
        except docker.errors.APIError as e:
            logger.error(f"Docker API Error while spawning {container_name}: {e}")
            raise RuntimeError(f"Failed to spawn project container: {e}") from e

    @staticmethod
    def get_project_data_plane_status(project_id: uuid.UUID) -> dict:
        """
        Inspects the status of a project Data Plane container.
        """
        container_name = f"unotusk-project-{str(project_id)[:8]}"
        try:
            client = docker.from_env()
            container = client.containers.get(container_name)
            port_bindings = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            assigned_port = None
            if "8000/tcp" in port_bindings and port_bindings["8000/tcp"]:
                assigned_port = int(port_bindings["8000/tcp"][0].get("HostPort"))

            return {
                "exists": True,
                "container_id": container.short_id,
                "status": container.status,
                "port": assigned_port,
                "is_running": container.status == "running",
            }
        except Exception:
            return {
                "exists": False,
                "container_id": None,
                "status": "not_found",
                "port": None,
                "is_running": False,
            }

    @staticmethod
    def stop_project_container(project_id: uuid.UUID) -> bool:
        """
        Stops and removes the project Data Plane container if present.
        """
        container_name = f"unotusk-project-{str(project_id)[:8]}"
        try:
            client = docker.from_env()
            container = client.containers.get(container_name)
            container.stop(timeout=5)
            container.remove()
            logger.info(f"Stopped and removed data plane container {container_name}.")
            return True
        except Exception as e:
            logger.warning(f"Could not stop data plane container {container_name}: {e}")
            return False
