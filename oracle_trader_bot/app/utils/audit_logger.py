# app/utils/audit_logger.py
"""
Audit Logger - Privacy-safe append-only audit logging for settings changes

Provides comprehensive audit logging with:
- Redacted secret values for privacy
- JSON-line format for efficient parsing
- Automatic log rotation when size exceeds limit
- Actor information (IP, User-Agent) when available
- Immutable append-only design
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from fastapi import Request

logger = logging.getLogger(__name__)

@dataclass
class AuditEntry:
    """Structured audit log entry"""
    timestamp: str
    actor: Dict[str, Optional[str]]
    changes: List[Dict[str, Any]]

class SettingsAuditLogger:
    """
    Append-only audit logger for settings changes with privacy protection.
    
    Features:
    - Redacts sensitive fields automatically
    - JSON-line format for efficient parsing
    - Automatic rotation when file exceeds size limit
    - Actor tracking (IP, User-Agent)
    """
    
    # Secret fields that should always be redacted
    SENSITIVE_FIELDS = {
        'KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_API_PASSPHRASE',
        'POSTGRES_PASSWORD', 'SETTINGS_ENCRYPTION_KEY'
    }
    
    # Additional fields that may contain sensitive info
    POTENTIALLY_SENSITIVE_FIELDS = {
        'DATABASE_URL', 'REDIS_URL'
    }
    
    def __init__(self, audit_dir: Path = None, max_file_size_mb: int = 5, max_generations: int = 3):
        """
        Initialize audit logger.
        
        Args:
            audit_dir: Directory for audit logs (default: .runtime)
            max_file_size_mb: Max file size before rotation
            max_generations: Number of rotated files to keep
        """
        self.audit_dir = audit_dir or Path(".runtime")
        self.audit_file = self.audit_dir / "audit.log"
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_generations = max_generations
        
        # Ensure audit directory exists with secure permissions
        self.audit_dir.mkdir(exist_ok=True, mode=0o700)
        
    def _redact_value(self, field: str, value: Any) -> str:
        """
        Redact sensitive values for privacy protection.
        
        Args:
            field: Field name to check sensitivity
            value: Raw value to potentially redact
            
        Returns:
            Original value or "<redacted>" for sensitive fields
        """
        if field in self.SENSITIVE_FIELDS:
            return "<redacted>"
        elif field in self.POTENTIALLY_SENSITIVE_FIELDS:
            # For potentially sensitive fields, redact if it looks like credentials
            if isinstance(value, str) and any(keyword in value.lower() for keyword in ['password', 'key', 'secret', 'token']):
                return "<redacted>"
        
        # Non-sensitive fields return as-is
        return value
        
    def _extract_actor_info(self, request: Optional[Request] = None) -> Dict[str, Optional[str]]:
        """
        Extract actor information from request context.
        
        Args:
            request: FastAPI request object if available
            
        Returns:
            Actor information dictionary
        """
        actor = {
            "ip": None,
            "user_agent": None
        }
        
        if request:
            # Extract IP address (handle proxies)
            actor["ip"] = request.client.host if request.client else None
            if not actor["ip"] and "x-forwarded-for" in request.headers:
                actor["ip"] = request.headers["x-forwarded-for"].split(",")[0].strip()
            elif not actor["ip"] and "x-real-ip" in request.headers:
                actor["ip"] = request.headers["x-real-ip"]
                
            # Extract User-Agent
            actor["user_agent"] = request.headers.get("user-agent")
            
        return actor
        
    def _create_audit_entry(self, old_values: Dict[str, Any], new_values: Dict[str, Any], 
                          request: Optional[Request] = None) -> AuditEntry:
        """
        Create audit entry from old and new values.
        
        Args:
            old_values: Previous settings values
            new_values: New settings values
            request: FastAPI request for actor info
            
        Returns:
            Structured audit entry
        """
        changes = []
        
        # Find all fields that changed
        all_fields = set(old_values.keys()) | set(new_values.keys())
        
        for field in all_fields:
            old_val = old_values.get(field)
            new_val = new_values.get(field)
            
            # Only log actual changes
            if old_val != new_val:
                changes.append({
                    "field": field,
                    "old": self._redact_value(field, old_val),
                    "new": self._redact_value(field, new_val)
                })
        
        return AuditEntry(
            timestamp=datetime.now().astimezone().isoformat(),
            actor=self._extract_actor_info(request),
            changes=changes
        )
        
    def _rotate_log_if_needed(self):
        """Rotate audit log if it exceeds size limit"""
        if not self.audit_file.exists():
            return
            
        if self.audit_file.stat().st_size > self.max_file_size_bytes:
            logger.info(f"Rotating audit log (size: {self.audit_file.stat().st_size / 1024 / 1024:.1f}MB)")
            
            # Rotate existing backups
            for i in range(self.max_generations - 1, 0, -1):
                old_backup = self.audit_dir / f"audit.log.{i}"
                new_backup = self.audit_dir / f"audit.log.{i + 1}"
                
                if old_backup.exists():
                    if new_backup.exists():
                        new_backup.unlink()  # Remove oldest
                    old_backup.rename(new_backup)
            
            # Move current log to .1
            backup_file = self.audit_dir / "audit.log.1"
            if backup_file.exists():
                backup_file.unlink()
            self.audit_file.rename(backup_file)
            
            logger.info(f"Audit log rotated successfully")
            
    def log_settings_change(self, old_values: Dict[str, Any], new_values: Dict[str, Any], 
                          request: Optional[Request] = None):
        """
        Log settings changes to audit file.
        
        Args:
            old_values: Previous settings values
            new_values: Updated settings values  
            request: FastAPI request for actor context
        """
        try:
            # Rotate if needed before writing
            self._rotate_log_if_needed()
            
            # Create audit entry
            entry = self._create_audit_entry(old_values, new_values, request)
            
            # Skip if no changes (shouldn't happen, but be safe)
            if not entry.changes:
                logger.debug("No changes detected, skipping audit log")
                return
                
            # Append to audit log (JSON Lines format)
            entry_json = json.dumps({
                "timestamp": entry.timestamp,
                "actor": entry.actor,
                "changes": entry.changes
            }, separators=(',', ':'))  # Compact JSON
            
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                f.write(entry_json + '\n')
                
            logger.info(f"Audit logged: {len(entry.changes)} field changes")
            
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            # Don't raise - audit failure shouldn't break the main operation
            
    def get_audit_entries(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """
        Retrieve paginated audit entries, newest first.
        
        Args:
            page: Page number (1-based)
            page_size: Number of entries per page
            
        Returns:
            Paginated audit data with metadata
        """
        try:
            if not self.audit_file.exists():
                return {
                    "entries": [],
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_entries": 0,
                        "total_pages": 0
                    }
                }
                
            # Read all entries (for small files this is fine)
            entries = []
            with open(self.audit_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON line in audit log: {e}")
                            continue
                            
            # Reverse for newest first
            entries.reverse()
            
            # Calculate pagination
            total_entries = len(entries)
            total_pages = (total_entries + page_size - 1) // page_size
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            page_entries = entries[start_idx:end_idx]
            
            return {
                "entries": page_entries,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_entries": total_entries,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to read audit entries: {e}")
            return {
                "entries": [],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_entries": 0,
                    "total_pages": 0
                },
                "error": str(e)
            }

# Global audit logger instance
audit_logger = SettingsAuditLogger()
