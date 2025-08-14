# backend/app/api/routers/logs.py
"""
Logs Router - Server Log Management & Monitoring

Provides access to server logs for monitoring, debugging, and system health analysis.
Supports filtering, searching, and real-time log retrieval from API server and bot engine.

Routes:
- GET /api/v1/logs/server-logs - Get server logs with filtering and search capabilities
"""

import os
import re
import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Regex patterns for parsing different log formats
# Standard log format: 2025-01-10 12:00:00 - module.name - INFO - Message
LOG_LINE_REGEX = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - "
    r"(?P<name>[a-zA-Z0-9\._-]+) - "
    r"(?P<level>INFO|WARNING|ERROR|CRITICAL|DEBUG) - "
    r"(?P<message>.*)$"
)

# Bot engine specific log format: includes [BotEngine] prefix
BOT_ENGINE_LOG_LINE_REGEX = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - "
    r"(?P<name>[a-zA-Z0-9\._-]+) - "
    r"(?P<level>INFO|WARNING|ERROR|CRITICAL|DEBUG) - "
    r"\[BotEngine\] (?P<message>.*)$"
)

@router.get(
    "/server-logs", # Full path: /api/v1/logs/server-logs
    summary="Get Server Logs",
    response_model=List[Dict[str, str]],
    tags=["Logs"]
)
async def get_server_logs(
    log_type: str = Query("all", description="Type of logs: 'api' for API server logs, 'bot' for bot engine logs, 'all' for combined"),
    limit: int = Query(200, gt=0, le=1000, description="Number of log lines to retrieve (1-1000)"),
    tail: bool = Query(True, description="If true, get the latest N lines. If false, get from the beginning"),
    level: Optional[str] = Query(None, description="Filter by log level (INFO, WARNING, ERROR, CRITICAL, DEBUG). Case-insensitive"),
    search: Optional[str] = Query(None, description="Search for specific text in log messages (case-insensitive)")
) -> List[Dict[str, str]]:
    """
    Retrieves server logs from specified log files with advanced filtering capabilities.
    
    Combines API server logs and bot engine logs into a unified view for system monitoring.
    Supports real-time log tailing, level filtering, and text search functionality.
    
    - **log_type**: Which logs to retrieve ('api', 'bot', or 'all')
    - **limit**: Maximum number of log entries to return (1-1000)
    - **tail**: Get latest entries (True) or oldest entries (False)  
    - **level**: Filter by specific log level (case-insensitive)
    - **search**: Search for text within log messages (case-insensitive)
    
    Returns parsed log entries with timestamp, level, source module, and message.
    """
    log_entries = []

    # Determine which log files to read
    log_files_to_read = []
    if log_type == "api":
        log_files_to_read.append(os.path.join(settings.LOG_DIR, settings.API_SERVER_LOG_FILE))
    elif log_type == "bot":
        log_files_to_read.append(os.path.join(settings.LOG_DIR, settings.BOT_ENGINE_LOG_FILE))
    elif log_type == "all":
        log_files_to_read.append(os.path.join(settings.LOG_DIR, settings.API_SERVER_LOG_FILE))
        log_files_to_read.append(os.path.join(settings.LOG_DIR, settings.BOT_ENGINE_LOG_FILE))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid log_type. Must be 'api', 'bot', or 'all'."
        )

    # Process each log file
    for log_file_path in log_files_to_read:
        if not os.path.exists(log_file_path):
            logger.warning(f"Log file not found: {log_file_path}")
            continue

        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
                # Get relevant lines based on 'tail' and 'limit'
                if tail:
                    relevant_lines = lines[-limit:]
                else:
                    relevant_lines = lines[:limit]

                # Parse each line
                for line in relevant_lines:
                    # Choose appropriate regex based on log file and content
                    regex_to_use = LOG_LINE_REGEX
                    if log_file_path.endswith(settings.BOT_ENGINE_LOG_FILE) and "[BotEngine]" in line:
                        regex_to_use = BOT_ENGINE_LOG_LINE_REGEX
                    
                    match = regex_to_use.match(line)
                    if match:
                        log_data = match.groupdict()
                        
                        # Apply level filter if provided
                        if level and log_data['level'].lower() != level.lower():
                            continue
                            
                        # Apply search filter if provided
                        if search and search.lower() not in log_data['message'].lower():
                            continue
                        
                        log_entry = {
                            "timestamp": log_data.get('timestamp', 'N/A'),
                            "level": log_data.get('level', 'UNKNOWN'),
                            "name": log_data.get('name', 'N/A'),
                            "message": log_data.get('message', '').strip()
                        }
                        log_entries.append(log_entry)
                    else:
                        # Handle lines that don't match regex (multi-line exceptions, raw logs)
                        current_level = "INFO"  # Default level for unparsed lines
                        if "ERROR" in line:
                            current_level = "ERROR"
                        elif "WARNING" in line:
                            current_level = "WARNING"
                        elif "CRITICAL" in line:
                            current_level = "CRITICAL"
                        elif "DEBUG" in line:
                            current_level = "DEBUG"

                        # Apply filters to raw lines
                        if level and current_level.lower() != level.lower():
                            continue
                        if search and search.lower() not in line.lower():
                            continue
                        
                        log_entries.append({
                            "timestamp": "N/A",  # Cannot parse timestamp for unformatted line
                            "level": current_level,
                            "name": "raw_log",
                            "message": line.strip()
                        })

        except Exception as e:
            logger.error(f"Error reading log file {log_file_path}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not read log file: {e}"
            )

    # Sort logs by timestamp if combining multiple log types
    if log_type == 'all' and log_entries:
        log_entries.sort(key=lambda x: x.get('timestamp', ''))

    return log_entries
