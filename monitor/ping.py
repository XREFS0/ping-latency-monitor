import subprocess
import sys
import re
import time
from typing import Tuple, Optional
from monitor.models import PingResult

class PingService:
    def __init__(self) -> None:
        self.time_pattern = re.compile(r"time[=<]([0-9.]+)\s*ms", re.IGNORECASE)

    def ping(self, address: str, timeout_ms: int) -> PingResult:
        is_windows = sys.platform == "win32"
        
        if is_windows:
            cmd = ["ping", "-n", "1", "-w", str(timeout_ms), address]
        else:
            timeout_sec = str(max(1, timeout_ms // 1000))
            cmd = ["ping", "-c", "1", "-W", timeout_sec, address]
            
        startupinfo = None
        if is_windows:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=(timeout_ms / 1000.0) + 1.0,
                startupinfo=startupinfo
            )
        except subprocess.TimeoutExpired:
            return PingResult(
                timestamp=start_time,
                latency=None,
                success=False,
                error_message="Timeout expired"
            )
        except Exception as e:
            return PingResult(
                timestamp=start_time,
                latency=None,
                success=False,
                error_message=str(e)
            )

        stdout = result.stdout
        if result.returncode != 0 and not is_windows:
            return PingResult(
                timestamp=start_time,
                latency=None,
                success=False,
                error_message=result.stderr.strip() or "Ping failed"
            )

        match = self.time_pattern.search(stdout)
        if match:
            try:
                latency = float(match.group(1))
                return PingResult(
                    timestamp=start_time,
                    latency=latency,
                    success=True
                )
            except ValueError:
                pass

        if "timed out" in stdout.lower() or "timeout" in stdout.lower():
            err = "Request timed out"
        elif "unreachable" in stdout.lower():
            err = "Destination host unreachable"
        elif "could not find host" in stdout.lower() or "name or service not known" in stdout.lower():
            err = "Host not found"
        else:
            err = "Ping execution failed"

        return PingResult(
            timestamp=start_time,
            latency=None,
            success=False,
            error_message=err
        )
