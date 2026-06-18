"""
Process manager for aircrack-ng tool subprocesses.
Handles launching, tracking, stdout capture, and cleanup.
"""

import subprocess
import threading
import signal
import os
import logging
from queue import Queue, Empty

log = logging.getLogger("airngui.process")


class ProcessManager:
    """Manages multiple concurrent subprocesses (e.g., airodump + aireplay)."""

    def __init__(self):
        self._processes = {}  # name -> ManagedProcess

    def start(self, name, cmd, on_output=None, on_exit=None):
        """
        Launch a subprocess.

        Args:
            name: unique key to track this process (e.g., 'airodump', 'aireplay')
            cmd: list of command args, e.g., ['airodump-ng', 'wlan0mon']
            on_output: callback(line: str) called per stdout line from a bg thread
            on_exit: callback(returncode: int) called when process exits
        Returns:
            ManagedProcess instance
        """
        # Kill existing process with same name
        if name in self._processes:
            self.stop(name)

        proc = ManagedProcess(name, cmd, on_output, on_exit)
        proc.start()
        self._processes[name] = proc
        log.info(f"Started process '{name}': {' '.join(cmd)} (PID {proc.proc.pid})")
        return proc

    def stop(self, name):
        """Stop a named process. Sends SIGTERM, then SIGKILL after 3s."""
        proc = self._processes.pop(name, None)
        if proc:
            log.info(f"Stopping process '{name}'")
            proc.stop()

    def stop_all(self):
        """Kill every tracked process. Call on app exit."""
        for name in list(self._processes.keys()):
            self.stop(name)

    def is_running(self, name):
        proc = self._processes.get(name)
        return proc is not None and proc.is_running()

    def get(self, name):
        return self._processes.get(name)


class ManagedProcess:
    """Wraps a single subprocess with threaded output reading."""

    def __init__(self, name, cmd, on_output=None, on_exit=None):
        self.name = name
        self.cmd = cmd
        self.on_output = on_output
        self.on_exit = on_exit
        self.proc = None
        self._reader_thread = None
        self.output_queue = Queue()

    def start(self):
        self.proc = subprocess.Popen(
            self.cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            # Don't let child inherit signals from parent
            preexec_fn=os.setsid,
            text=True,
            bufsize=1,
        )
        # Background thread reads stdout so we never block the GUI
        self._reader_thread = threading.Thread(
            target=self._read_output, daemon=True
        )
        self._reader_thread.start()

    def _read_output(self):
        try:
            for line in self.proc.stdout:
                line = line.rstrip("\n")
                self.output_queue.put(line)
                if self.on_output:
                    self.on_output(line)
        except (ValueError, OSError) as e:
            log.debug(f"Process '{self.name}' pipe closed: {e}")
        finally:
            retcode = self.proc.wait()
            if retcode != 0:
                log.warning(f"Process '{self.name}' exited with code {retcode}")
            else:
                log.info(f"Process '{self.name}' exited cleanly")
            if self.on_exit:
                self.on_exit(retcode)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                # Kill entire process group (important for aircrack tools
                # that may spawn children)
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def drain_queue(self):
        """Pull all pending lines from the output queue. Non-blocking."""
        lines = []
        while True:
            try:
                lines.append(self.output_queue.get_nowait())
            except Empty:
                break
        return lines


def run_quick(cmd, timeout=10):
    """
    Run a short-lived command and return (returncode, stdout).
    For things like `airmon-ng` (no args) that list interfaces and exit.
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout
    except subprocess.TimeoutExpired:
        return -1, "Command timed out"
    except FileNotFoundError:
        return -1, f"Command not found: {cmd[0]}"
