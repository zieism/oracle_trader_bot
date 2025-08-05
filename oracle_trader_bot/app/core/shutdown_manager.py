# app/core/shutdown_manager.py
import asyncio
import logging
import signal
import sys
from typing import Optional, Callable, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ShutdownManager:
    """
    Centralized shutdown management for graceful bot termination.
    Handles signal registration, task cancellation, and resource cleanup.
    """
    
    def __init__(self):
        self.shutdown_initiated = False
        self.cleanup_callbacks: List[Callable] = []
        self.shutdown_event: Optional[asyncio.Event] = None
        
    def add_cleanup_callback(self, callback: Callable):
        """Add a cleanup callback to be called during shutdown."""
        self.cleanup_callbacks.append(callback)
        
    def create_shutdown_event(self) -> asyncio.Event:
        """Create and return a shutdown event that can be awaited."""
        if self.shutdown_event is None:
            self.shutdown_event = asyncio.Event()
        return self.shutdown_event
        
    async def signal_handler_async(self):
        """Async signal handler for graceful shutdown."""
        if self.shutdown_initiated:
            logger.info("ShutdownManager: Graceful shutdown already initiated. Ignoring redundant signal.")
            return
            
        self.shutdown_initiated = True
        logger.info("ShutdownManager: Received OS signal (SIGINT/SIGTERM). Starting graceful shutdown...")
        
        # Set shutdown event if it exists
        if self.shutdown_event:
            self.shutdown_event.set()
            
        # Get all running tasks excluding the current one
        current_task = asyncio.current_task()
        all_tasks = [task for task in asyncio.all_tasks() if task != current_task and not task.done()]
        
        if all_tasks:
            logger.info(f"ShutdownManager: Cancelling {len(all_tasks)} running tasks...")
            for task in all_tasks:
                task.cancel()
                
            # Wait for tasks to complete cancellation
            try:
                await asyncio.wait_for(asyncio.gather(*all_tasks, return_exceptions=True), timeout=10.0)
                logger.info("ShutdownManager: All tasks cancelled successfully.")
            except asyncio.TimeoutError:
                logger.warning("ShutdownManager: Some tasks did not finish cancelling within timeout.")
            except Exception as e:
                logger.error(f"ShutdownManager: Error during task cancellation: {e}", exc_info=True)
                
        # Execute cleanup callbacks
        await self.execute_cleanup_callbacks()
        
        # Save final state
        await self.save_shutdown_state()
        
        logger.info("ShutdownManager: Graceful shutdown completed.")
        
    async def execute_cleanup_callbacks(self):
        """Execute all registered cleanup callbacks."""
        logger.info(f"ShutdownManager: Executing {len(self.cleanup_callbacks)} cleanup callbacks...")
        
        for i, callback in enumerate(self.cleanup_callbacks):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
                logger.debug(f"ShutdownManager: Cleanup callback {i+1} completed.")
            except Exception as e:
                logger.error(f"ShutdownManager: Error in cleanup callback {i+1}: {e}", exc_info=True)
                
    async def save_shutdown_state(self):
        """Save shutdown state and timestamp for monitoring purposes."""
        try:
            shutdown_info = {
                "timestamp": datetime.now().isoformat(),
                "clean_shutdown": True,
                "callbacks_executed": len(self.cleanup_callbacks)
            }
            logger.info(f"ShutdownManager: Shutdown state saved: {shutdown_info}")
        except Exception as e:
            logger.error(f"ShutdownManager: Error saving shutdown state: {e}", exc_info=True)
            
    def register_signal_handlers(self, loop: asyncio.AbstractEventLoop):
        """Register signal handlers for graceful shutdown."""
        for sig_name in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(
                    sig_name, 
                    lambda: loop.create_task(self.signal_handler_async())
                )
                logger.info(f"ShutdownManager: Registered signal handler for {sig_name.name}.")
            except (NotImplementedError, RuntimeError) as e:
                logger.warning(f"ShutdownManager: Could not register signal handler for {sig_name.name}: {e}")
                
    def force_exit(self, exit_code: int = 0):
        """Force exit the process after cleanup."""
        logger.info(f"ShutdownManager: Force exiting with code {exit_code}")
        sys.exit(exit_code)


# Global shutdown manager instance
shutdown_manager = ShutdownManager()