# app/core/bot_process_manager.py
import subprocess
import os
import signal
import logging
import sys
import time 
from typing import Optional, Tuple

# Attempt to import psutil for more reliable process checking
try:
    import psutil
except ImportError:
    psutil = None
    logging.warning("psutil not found. Process status checks might be less robust.")

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BOT_ENGINE_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "bot_engine.py")
PID_FILE = os.path.join(PROJECT_ROOT, "bot_engine.pid") 

def _is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    if psutil:
        try:
            # Check if PID exists and is not a zombie process
            proc = psutil.Process(pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied:
            logger.warning(f"Access denied to process {pid} with psutil. Falling back to os.kill(pid, 0).")
            try:
                os.kill(pid, 0) # Signal 0 doesn't do anything, but checks if PID exists
                return True
            except OSError:
                return False
    else:
        try:
            os.kill(pid, 0) 
            return True
        except OSError:
            return False

def get_bot_process_status() -> Tuple[str, Optional[int]]:
    """Get the current status of the bot process."""
    if not os.path.exists(PID_FILE):
        logger.debug(f"PID file '{PID_FILE}' not found. Bot assumed stopped.")
        return "stopped", None
    try:
        with open(PID_FILE, "r") as f:
            pid_str = f.read().strip()
            if not pid_str:
                logger.warning(f"PID file '{PID_FILE}' is empty. Cleaning up.")
                os.remove(PID_FILE) 
                return "stopped", None
            pid = int(pid_str)
    except (IOError, ValueError) as e:
        logger.warning(f"Error reading PID file '{PID_FILE}': {e}. Cleaning up.")
        try:
            os.remove(PID_FILE) 
        except OSError:
            pass
        return "stopped", None

    if _is_process_running(pid):
        return "running", pid 
    else:
        logger.warning(f"Bot process with PID {pid} from PID file not found. Cleaning up stale PID file.")
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        return "stopped_stale_pid", None

def start_bot_engine() -> Tuple[bool, str]:
    """Start the bot engine as a detached process."""
    status, pid = get_bot_process_status()
    if status == "running" and pid is not None:
        logger.info(f"Attempt to start bot, but it is already running with PID {pid}.")
        return False, f"Bot engine is already running with PID {pid}."

    if not os.path.exists(BOT_ENGINE_SCRIPT_PATH):
        logger.error(f"Bot engine script not found at '{BOT_ENGINE_SCRIPT_PATH}'")
        return False, f"Bot engine script not found. Expected at: '{BOT_ENGINE_SCRIPT_PATH}'."

    try:
        python_executable = sys.executable 
        # Ensure log directory exists if using specific files
        log_dir = os.path.join(PROJECT_ROOT, "logs")
        os.makedirs(log_dir, exist_ok=True)
        stdout_path = os.path.join(log_dir, "bot_engine_stdout.log")
        stderr_path = os.path.join(log_dir, "bot_engine_stderr.log")

        logger.info(f"Starting bot engine script: {python_executable} {BOT_ENGINE_SCRIPT_PATH}")
        process = subprocess.Popen(
            [python_executable, BOT_ENGINE_SCRIPT_PATH],
            cwd=PROJECT_ROOT,
            preexec_fn=os.setsid, # Detach from parent process group. This PID will be the PGID.
            stdout=open(stdout_path, "a"), # Open file handles for stdout/stderr
            stderr=open(stderr_path, "a"),
            close_fds=True # Close file descriptors in child process
        )
        with open(PID_FILE, "w") as f:
            f.write(str(process.pid)) # Store PID (which is also the PGID here)
        logger.info(f"Bot engine started successfully with PID {process.pid}. Stdout/Stderr redirected to {stdout_path}, {stderr_path}.")
        return True, f"Bot engine started with PID {process.pid}."
    except Exception as e:
        logger.error(f"Failed to start bot engine: {e}", exc_info=True)
        return False, f"Failed to start bot engine: {str(e)}"

def stop_bot_engine() -> Tuple[bool, str]:
    """Stop the bot engine process by sending signals to its process group."""
    status, pid = get_bot_process_status()

    if pid is None or status.startswith("stopped"):
        logger.info(f"Attempt to stop bot, but it is not considered running. Status: {status}")
        if os.path.exists(PID_FILE): # Ensure PID file is cleaned up if it was stale
            try: os.remove(PID_FILE)
            except OSError: pass
        return True, f"Bot engine is not running (status: {status})."
        
    try:
        # Send SIGINT to the process group ID (-pid) to ensure all child processes/threads receive it
        logger.info(f"Attempting to stop bot engine with PID {pid} by sending SIGINT to process group {-pid}...")
        os.kill(-pid, signal.SIGINT) # Send signal to process group
        
        max_wait_seconds_sigint = 15 # Increased wait time for graceful shutdown
        wait_interval = 1   
        elapsed_wait = 0

        while elapsed_wait < max_wait_seconds_sigint:
            time.sleep(wait_interval)
            elapsed_wait += wait_interval
            if not _is_process_running(pid):
                logger.info(f"Bot engine (PID {pid}) terminated gracefully after {elapsed_wait}s (SIGINT).")
                if os.path.exists(PID_FILE): os.remove(PID_FILE)
                return True, f"Bot engine (PID {pid}) stopped successfully via SIGINT."
            logger.debug(f"Waiting for bot (PID {pid}) to terminate... ({elapsed_wait}/{max_wait_seconds_sigint}s)")

        # If SIGINT didn't work, send SIGTERM to the process group
        logger.warning(f"Bot engine (PID {pid}) did not terminate after {max_wait_seconds_sigint}s with SIGINT. Sending SIGTERM to process group {-pid}...")
        os.kill(-pid, signal.SIGTERM)
        
        max_wait_seconds_sigterm = 5 # Shorter wait for SIGTERM
        elapsed_wait_term = 0
        while elapsed_wait_term < max_wait_seconds_sigterm:
            time.sleep(wait_interval)
            elapsed_wait_term += wait_interval
            if not _is_process_running(pid):
                logger.info(f"Bot engine (PID {pid}) terminated after {elapsed_wait_term}s (SIGTERM).")
                if os.path.exists(PID_FILE): os.remove(PID_FILE)
                return True, f"Bot engine (PID {pid}) stopped successfully via SIGTERM."
            logger.debug(f"Waiting for bot (PID {pid}) to terminate after SIGTERM... ({elapsed_wait_term}/{max_wait_seconds_sigterm}s)")

        logger.error(f"Bot engine (PID {pid}) could not be terminated even with SIGTERM. Manual intervention required.")
        return False, f"Bot engine (PID {pid}) could not be terminated. Manual check required."
            
    except ProcessLookupError: 
        logger.warning(f"Bot engine process with PID {pid} not found (ProcessLookupError - already stopped?). Cleaning up PID file.")
        if os.path.exists(PID_FILE):
            try: os.remove(PID_FILE)
            except OSError: pass
        return True, "Bot engine process not found (already stopped or PID file stale)."
    except Exception as e: 
        logger.error(f"Unexpected error stopping bot engine with PID {pid}: {e}", exc_info=True)
        return False, f"Unexpected error stopping bot engine: {str(e)}"