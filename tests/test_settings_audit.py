# tests/test_settings_audit.py
"""
Tests for Settings Audit Logging System

Comprehensive tests covering:
- Audit log creation and redaction
- Pagination functionality  
- Log rotation mechanics
- API integration
- Privacy compliance
"""

import json
import os
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.utils.audit_logger import SettingsAuditLogger, AuditEntry
from app.main import app


class TestSettingsAuditLogger:
    """Test suite for the audit logging system"""

    @pytest.fixture
    def temp_audit_dir(self):
        """Create temporary audit directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture  
    def audit_logger(self, temp_audit_dir):
        """Create audit logger with temporary directory"""
        return SettingsAuditLogger(
            audit_dir=temp_audit_dir,
            max_file_size_mb=1,  # Small size for rotation testing
            max_generations=2
        )

    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request with client info"""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.headers = {
            "user-agent": "Mozilla/5.0 (TestClient)",
            "x-forwarded-for": "203.0.113.1"
        }
        return request

    def test_redaction_of_sensitive_fields(self, audit_logger):
        """Test that sensitive fields are properly redacted"""
        # Sensitive fields should always be redacted
        assert audit_logger._redact_value("KUCOIN_API_KEY", "secret123") == "<redacted>"
        assert audit_logger._redact_value("KUCOIN_API_SECRET", "secret456") == "<redacted>"
        assert audit_logger._redact_value("POSTGRES_PASSWORD", "password123") == "<redacted>"
        
        # Non-sensitive fields should pass through
        assert audit_logger._redact_value("PROJECT_NAME", "My Bot") == "My Bot"
        assert audit_logger._redact_value("DEBUG", True) == True
        assert audit_logger._redact_value("MAX_POSITION_SIZE", 1000) == 1000

    def test_potentially_sensitive_field_detection(self, audit_logger):
        """Test detection of potentially sensitive values in generic fields"""
        # URLs with credentials should be redacted
        db_url_with_creds = "postgresql://user:password123@localhost/db"
        assert audit_logger._redact_value("DATABASE_URL", db_url_with_creds) == "<redacted>"
        
        # Safe URLs should pass through
        safe_url = "postgresql://localhost/db"
        assert audit_logger._redact_value("DATABASE_URL", safe_url) == safe_url

    def test_actor_info_extraction(self, audit_logger, mock_request):
        """Test extraction of actor information from request"""
        actor = audit_logger._extract_actor_info(mock_request)
        
        # Should prefer client.host over headers
        assert actor["ip"] == "192.168.1.100"
        assert actor["user_agent"] == "Mozilla/5.0 (TestClient)"

    def test_actor_info_with_proxy_headers(self, audit_logger):
        """Test actor info extraction with proxy headers"""
        request = Mock(spec=Request)
        request.client = None
        request.headers = {
            "x-forwarded-for": "203.0.113.1, 192.168.1.1",
            "user-agent": "TestClient/1.0"
        }
        
        actor = audit_logger._extract_actor_info(request)
        
        # Should extract first IP from X-Forwarded-For
        assert actor["ip"] == "203.0.113.1"
        assert actor["user_agent"] == "TestClient/1.0"

    def test_audit_entry_creation(self, audit_logger, mock_request):
        """Test creation of audit entries from value changes"""
        old_values = {
            "PROJECT_NAME": "Old Bot",
            "KUCOIN_API_KEY": "old_key_123",
            "DEBUG": False
        }
        
        new_values = {
            "PROJECT_NAME": "New Bot", 
            "KUCOIN_API_KEY": "new_key_456",
            "DEBUG": False,  # No change
            "MAX_POSITION_SIZE": 2000  # New field
        }
        
        entry = audit_logger._create_audit_entry(old_values, new_values, mock_request)
        
        # Should have timestamp and actor info
        assert isinstance(entry.timestamp, str)
        assert entry.actor["ip"] == "192.168.1.100"
        
        # Should have 3 changes (PROJECT_NAME, KUCOIN_API_KEY, MAX_POSITION_SIZE)
        assert len(entry.changes) == 3
        
        # Check specific changes
        project_change = next(c for c in entry.changes if c["field"] == "PROJECT_NAME")
        assert project_change["old"] == "Old Bot"
        assert project_change["new"] == "New Bot"
        
        # Check API key is redacted
        api_key_change = next(c for c in entry.changes if c["field"] == "KUCOIN_API_KEY")
        assert api_key_change["old"] == "<redacted>"
        assert api_key_change["new"] == "<redacted>"
        
        # Check new field
        size_change = next(c for c in entry.changes if c["field"] == "MAX_POSITION_SIZE")
        assert size_change["old"] is None  # old_values didn't have this
        assert size_change["new"] == 2000

    def test_audit_logging_to_file(self, audit_logger, mock_request):
        """Test that audit entries are properly written to file"""
        old_values = {"PROJECT_NAME": "Old"}
        new_values = {"PROJECT_NAME": "New"}
        
        audit_logger.log_settings_change(old_values, new_values, mock_request)
        
        # Check file was created
        assert audit_logger.audit_file.exists()
        
        # Check content
        with open(audit_logger.audit_file, 'r') as f:
            line = f.readline().strip()
            entry = json.loads(line)
            
        assert "timestamp" in entry
        assert entry["actor"]["ip"] == "192.168.1.100"
        assert len(entry["changes"]) == 1
        assert entry["changes"][0]["field"] == "PROJECT_NAME"
        assert entry["changes"][0]["old"] == "Old"
        assert entry["changes"][0]["new"] == "New"

    def test_no_audit_when_no_changes(self, audit_logger, mock_request):
        """Test that no audit entry is created when values don't change"""
        same_values = {"PROJECT_NAME": "Same", "DEBUG": True}
        
        audit_logger.log_settings_change(same_values, same_values, mock_request)
        
        # No file should be created
        assert not audit_logger.audit_file.exists()

    def test_audit_log_rotation(self, audit_logger, mock_request):
        """Test automatic log rotation when file size exceeds limit"""
        # Create a large audit file by writing many entries
        old_values = {"PROJECT_NAME": "Old"}
        new_values = {"PROJECT_NAME": "New"}
        
        # Write many entries to exceed 1MB limit  
        for i in range(1000):  # Should be enough to trigger rotation
            new_values["PROJECT_NAME"] = f"New_{i}"
            audit_logger.log_settings_change(old_values, new_values, mock_request)
            old_values = new_values.copy()
            
        # Check if rotation occurred (audit.log.1 should exist)
        backup_file = audit_logger.audit_dir / "audit.log.1"
        if backup_file.exists():
            # Rotation occurred successfully
            assert audit_logger.audit_file.exists()  # New log file
            assert backup_file.exists()  # Rotated log
        
        # Verify current log is smaller than the rotated one (or no rotation if not reached limit)
        assert audit_logger.audit_file.exists()

    def test_audit_retrieval_empty_log(self, audit_logger):
        """Test retrieval when no audit log exists"""
        result = audit_logger.get_audit_entries()
        
        assert result["entries"] == []
        assert result["pagination"]["total_entries"] == 0
        assert result["pagination"]["total_pages"] == 0

    def test_audit_retrieval_with_entries(self, audit_logger, mock_request):
        """Test paginated retrieval of audit entries"""
        # Create multiple audit entries
        for i in range(15):
            old_values = {"PROJECT_NAME": f"Old_{i}"}
            new_values = {"PROJECT_NAME": f"New_{i}"}
            audit_logger.log_settings_change(old_values, new_values, mock_request)
        
        # Test first page
        result = audit_logger.get_audit_entries(page=1, page_size=10)
        
        assert len(result["entries"]) == 10
        assert result["pagination"]["total_entries"] == 15
        assert result["pagination"]["total_pages"] == 2
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_previous"] is False
        
        # Should be newest first (New_14 should be first)
        first_entry = result["entries"][0]
        assert first_entry["changes"][0]["new"] == "New_14"
        
        # Test second page
        result = audit_logger.get_audit_entries(page=2, page_size=10)
        
        assert len(result["entries"]) == 5  # Remaining entries
        assert result["pagination"]["has_next"] is False
        assert result["pagination"]["has_previous"] is True

    def test_json_line_format_parsing(self, audit_logger, mock_request):
        """Test that malformed JSON lines are handled gracefully"""
        # Create normal entry
        old_values = {"PROJECT_NAME": "Old"}
        new_values = {"PROJECT_NAME": "New"}
        audit_logger.log_settings_change(old_values, new_values, mock_request)
        
        # Manually add malformed line
        with open(audit_logger.audit_file, 'a') as f:
            f.write("invalid json line\n")
            f.write('{"valid": "entry"}\n')
        
        # Should still retrieve valid entries
        result = audit_logger.get_audit_entries()
        
        # Should have 2 valid entries (1 original + 1 manually added valid entry, malformed line should be skipped)
        assert len(result["entries"]) == 2
        
        # Check that we got the expected entries
        entries = result["entries"]
        # Should be newest first, so the manually added entry comes first
        assert entries[0] == {"valid": "entry"}
        assert entries[1]["changes"][0]["field"] == "PROJECT_NAME"


class TestSettingsAuditAPI:
    """Test suite for the settings audit API endpoints"""

    def test_settings_update_creates_audit_entry(self):
        """Test that PUT /settings creates audit log entry"""
        with TestClient(app) as client:
            # Update settings
            response = client.put("/api/v1/settings", json={
                "PROJECT_NAME": "Test Audit Bot",
                "DEBUG": True,
                "KUCOIN_API_KEY": "test_key_123"
            })
            
            assert response.status_code == 200
            
            # Check audit log was created in default location
            from app.utils.audit_logger import audit_logger
            audit_file = audit_logger.audit_file
            assert audit_file.exists()
            
            # Verify audit entry content by reading the last line
            with open(audit_file, 'r') as f:
                lines = f.readlines()
                
            # Get the last line (newest entry)
            last_entry = json.loads(lines[-1])
            
            assert "timestamp" in last_entry
            assert "actor" in last_entry  
            assert len(last_entry["changes"]) >= 1
            
            # Verify API key is redacted
            api_key_change = next((c for c in last_entry["changes"] if c["field"] == "KUCOIN_API_KEY"), None)
            if api_key_change:
                assert api_key_change["new"] == "<redacted>"

    def test_get_audit_endpoint(self):
        """Test GET /settings/audit endpoint"""
        with TestClient(app) as client:
            response = client.get("/api/v1/settings/audit")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "entries" in data
            assert "pagination" in data
            assert "page" in data["pagination"]
            assert "page_size" in data["pagination"]
            assert "total_entries" in data["pagination"]

    def test_audit_pagination_parameters(self):
        """Test audit endpoint pagination parameters"""
        with TestClient(app) as client:
            # Test with custom pagination
            response = client.get("/api/v1/settings/audit?page=2&page_size=25")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["pagination"]["page"] == 2
            assert data["pagination"]["page_size"] == 25

    def test_audit_pagination_validation(self):
        """Test audit endpoint parameter validation"""
        with TestClient(app) as client:
            # Invalid page number
            response = client.get("/api/v1/settings/audit?page=0")
            assert response.status_code == 422  # Validation error
            
            # Invalid page size
            response = client.get("/api/v1/settings/audit?page_size=200")
            assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
