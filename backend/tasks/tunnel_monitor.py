"""SSH Tunnel and GPU Server health monitoring."""

import asyncio
import httpx
import structlog
import subprocess
import time
from typing import Optional
from core.config import settings

log = structlog.get_logger()


class TunnelHealthMonitor:
    """Monitors SSH tunnel and GPU server health, triggers restart if needed."""

    def __init__(
        self,
        comfyui_url: str = "http://localhost:8188",
        vllm_url: str = "http://localhost:8100",
        check_interval: int = 30,
        failure_threshold: int = 3,
    ):
        self.comfyui_url = comfyui_url
        self.vllm_url = vllm_url
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold

        self.consecutive_failures = 0
        self.last_check_time: Optional[float] = None
        self.is_healthy = True

    async def check_health(self) -> bool:
        """
        Check if GPU server (ComfyUI + vLLM) is accessible.

        Returns:
            True if healthy, False if unreachable
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try both endpoints
                tasks = [
                    client.get(f"{self.comfyui_url}/system_stats"),
                    client.get(f"{self.vllm_url}/v1/models"),
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Check if at least one succeeded (ComfyUI is more reliable)
                comfyui_ok = not isinstance(results[0], Exception) and results[0].status_code == 200
                vllm_ok = not isinstance(results[1], Exception) and results[1].status_code == 200

                is_ok = comfyui_ok or vllm_ok

                if is_ok:
                    self.consecutive_failures = 0
                    if not self.is_healthy:
                        log.info("tunnel_recovered")
                        self.is_healthy = True
                    return True
                else:
                    self.consecutive_failures += 1
                    log.warning(
                        "tunnel_health_check_failed",
                        consecutive_failures=self.consecutive_failures,
                        comfyui_ok=comfyui_ok,
                        vllm_ok=vllm_ok,
                    )
                    return False

        except Exception as e:
            self.consecutive_failures += 1
            log.warning(
                "tunnel_health_check_error",
                error=str(e),
                consecutive_failures=self.consecutive_failures,
            )
            return False

    async def run_monitor_loop(self):
        """
        Continuously monitor tunnel health.

        Triggers restart if failures exceed threshold.
        """
        log.info("tunnel_monitor_started", check_interval=self.check_interval)

        while True:
            try:
                await asyncio.sleep(self.check_interval)

                is_healthy = await self.check_health()

                # If we've had too many failures, attempt restart
                if self.consecutive_failures >= self.failure_threshold:
                    if self.is_healthy:  # Only log once
                        self.is_healthy = False
                        log.error(
                            "tunnel_unhealthy",
                            consecutive_failures=self.consecutive_failures,
                            threshold=self.failure_threshold,
                        )

                    # Attempt auto-restart
                    await self._attempt_restart()

            except asyncio.CancelledError:
                log.info("tunnel_monitor_stopped")
                break
            except Exception as e:
                log.error("tunnel_monitor_error", error=str(e))
                await asyncio.sleep(self.check_interval)

    async def _attempt_restart(self):
        """
        Attempt to restart the SSH tunnel.

        On Windows: runs PowerShell script
        On Linux: runs bash script
        """
        try:
            log.warning("tunnel_restart_attempt", threshold_failures=self.consecutive_failures)

            # Detect OS and run appropriate script
            import platform
            import os

            if platform.system() == "Windows":
                # Windows: PowerShell script
                script_path = "infra/scripts/restart-gpu-tunnel.ps1"
                if os.path.exists(script_path):
                    # Run PowerShell in background
                    subprocess.Popen(
                        ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    log.info("tunnel_restart_triggered_windows", script=script_path)
            else:
                # Linux: bash script
                script_path = "infra/scripts/restart-gpu-tunnel.sh"
                if os.path.exists(script_path):
                    subprocess.Popen(
                        ["bash", script_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    log.info("tunnel_restart_triggered_linux", script=script_path)
                else:
                    log.warning("tunnel_restart_script_not_found", path=script_path)

            # Wait before next health check (give restart time to work)
            await asyncio.sleep(5)

        except Exception as e:
            log.error("tunnel_restart_failed", error=str(e))


# Global monitor instance
_tunnel_monitor: Optional[TunnelHealthMonitor] = None


async def start_tunnel_monitor():
    """Start the tunnel health monitor as a background task."""
    global _tunnel_monitor

    if not settings.comfyui_url:
        log.warning("tunnel_monitor_disabled", reason="comfyui_url not configured")
        return None

    _tunnel_monitor = TunnelHealthMonitor(
        comfyui_url=settings.comfyui_url or "http://localhost:8188",
        vllm_url=settings.inference_api_base_url or "http://localhost:8100",
        check_interval=30,  # Check every 30 seconds
        failure_threshold=3,  # Restart after 3 consecutive failures (90 seconds)
    )

    # Run monitor in background
    task = asyncio.create_task(_tunnel_monitor.run_monitor_loop())
    log.info("tunnel_monitor_initialized")
    return task


def stop_tunnel_monitor():
    """Stop the tunnel health monitor."""
    global _tunnel_monitor
    if _tunnel_monitor:
        log.info("tunnel_monitor_stopping")
        _tunnel_monitor = None
