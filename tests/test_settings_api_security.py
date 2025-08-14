# tests/test_settings_api_security.py
"""
Integration tests for settings API security behavior:
- GET always returns masked secrets
- PUT preserves existing secrets when empty/*** provided
- Error messages don't leak secret values
"""

import pytest
import json
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "oracle_trader_bot"))

from app.main import app
from app.crud.crud_settings import settings_manager
from app.core.config import settings


class TestSettingsAPISecurity:
    """Test settings API security behavior"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def temp_settings_setup(self):
        """Setup temporary settings for testing"""
        # Store original values
        original_runtime_dir = settings_manager.runtime_dir
        original_settings_file = settings_manager.settings_file
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        settings_manager.runtime_dir = Path(temp_dir) / ".runtime"
        settings_manager.settings_file = settings_manager.runtime_dir / "settings.json"
        settings_manager._ensure_runtime_dir()
        
        # Setup some initial settings with secrets
        initial_settings = {
            'PROJECT_NAME': 'Test Project',
            'KUCOIN_API_KEY': 'existing_api_key_123',
            'KUCOIN_API_SECRET': 'existing_secret_456',
            'KUCOIN_API_PASSPHRASE': 'existing_pass_789',
            'POSTGRES_PASSWORD': 'existing_db_pass',
            'KUCOIN_SANDBOX': True,
            'DEBUG': True
        }
        settings_manager._save_file_settings(initial_settings)
        
        yield
        
        # Restore original values
        settings_manager.runtime_dir = original_runtime_dir
        settings_manager.settings_file = original_settings_file
        
        # Cleanup temp directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_get_settings_always_masks_secrets(self, client, temp_settings_setup):
        """Test that GET /api/v1/settings always returns masked secrets"""
        response = client.get("/api/v1/settings/")
        
        assert response.status_code == 200
        data = response.json()
        
        # All secrets should be masked
        assert data['KUCOIN_API_KEY'] == "***"
        assert data['KUCOIN_API_SECRET'] == "***"
        assert data['KUCOIN_API_PASSPHRASE'] == "***"
        assert data['POSTGRES_PASSWORD'] == "***"
        
        # Non-secrets should be visible
        assert data['PROJECT_NAME'] == "Test Project"
        assert data['KUCOIN_SANDBOX'] is True
    
    def test_put_preserves_secrets_on_empty_values(self, client, temp_settings_setup):
        """Test that PUT preserves existing secrets when empty/*** values provided"""
        # Update with mixed values - some secrets empty, some with new values
        update_data = {
            "PROJECT_NAME": "Updated Project",
            "KUCOIN_API_KEY": "",  # Empty - should preserve existing
            "KUCOIN_API_SECRET": "   ",  # Whitespace - should preserve existing  
            "KUCOIN_API_PASSPHRASE": "***",  # Masked - should preserve existing
            "POSTGRES_PASSWORD": "new_password_123",  # New value - should update
            "KUCOIN_SANDBOX": False,  # Non-secret - should update
            "DEBUG": False
        }
        
        response = client.put("/api/v1/settings/", json=update_data)
        assert response.status_code == 200
        
        # Verify response masks all secrets
        response_data = response.json()
        assert response_data['KUCOIN_API_KEY'] == "***"
        assert response_data['KUCOIN_API_SECRET'] == "***"
        assert response_data['KUCOIN_API_PASSPHRASE'] == "***"
        assert response_data['POSTGRES_PASSWORD'] == "***"
        
        # Non-secrets should be updated
        assert response_data['PROJECT_NAME'] == "Updated Project"
        assert response_data['KUCOIN_SANDBOX'] is False
        assert response_data['DEBUG'] is False
        
        # Check that file was updated with preserved secrets
        file_data = settings_manager._load_file_settings()
        assert file_data is not None
        
        # Existing secrets should be preserved (not empty/masked)
        assert file_data['KUCOIN_API_KEY'] == "existing_api_key_123"
        assert file_data['KUCOIN_API_SECRET'] == "existing_secret_456"
        assert file_data['KUCOIN_API_PASSPHRASE'] == "existing_pass_789"
        
        # New password should be updated
        assert file_data['POSTGRES_PASSWORD'] == "new_password_123"
        
        # Non-secrets should be updated
        assert file_data['PROJECT_NAME'] == "Updated Project"
        assert file_data['KUCOIN_SANDBOX'] is False
    
    def test_put_updates_valid_new_secrets(self, client, temp_settings_setup):
        """Test that PUT updates secrets when valid new values provided"""
        update_data = {
            "KUCOIN_API_KEY": "new_api_key_456",
            "KUCOIN_API_SECRET": "new_secret_789",
            "PROJECT_NAME": "Another Update"
        }
        
        response = client.put("/api/v1/settings/", json=update_data)
        assert response.status_code == 200
        
        # Response should mask secrets
        response_data = response.json()
        assert response_data['KUCOIN_API_KEY'] == "***"
        assert response_data['KUCOIN_API_SECRET'] == "***"
        
        # Check file has new secrets
        file_data = settings_manager._load_file_settings()
        assert file_data['KUCOIN_API_KEY'] == "new_api_key_456"
        assert file_data['KUCOIN_API_SECRET'] == "new_secret_789"
        
        # Unspecified secrets should be preserved
        assert file_data['KUCOIN_API_PASSPHRASE'] == "existing_pass_789"
    
    def test_put_validation_errors_dont_leak_secrets(self, client, temp_settings_setup):
        """Test that validation errors don't leak secret values"""
        # Try to set invalid secret (too short)
        update_data = {
            "KUCOIN_API_KEY": "short",  # Too short - should fail validation
            "PROJECT_NAME": "Test"
        }
        
        response = client.put("/api/v1/settings/", json=update_data)
        assert response.status_code == 500  # Should fail
        
        error_detail = response.json()['detail']
        
        # Error should mention the field but not leak the actual value
        assert "KUCOIN_API_KEY" in error_detail
        assert "at least 8 characters" in error_detail
        assert "short" not in error_detail  # Should not leak the actual value
    
    def test_put_empty_request_preserves_all_settings(self, client, temp_settings_setup):
        """Test that PUT with empty/null fields preserves all existing settings"""
        # Send update with only null/empty values
        update_data = {
            "KUCOIN_API_KEY": None,
            "KUCOIN_API_SECRET": "",
            "POSTGRES_PASSWORD": "***"
        }
        
        response = client.put("/api/v1/settings/", json=update_data)
        assert response.status_code == 200
        
        # File should retain original secrets
        file_data = settings_manager._load_file_settings()
        assert file_data['KUCOIN_API_KEY'] == "existing_api_key_123"
        assert file_data['KUCOIN_API_SECRET'] == "existing_secret_456"
        assert file_data['POSTGRES_PASSWORD'] == "existing_db_pass"
    
    def test_multiple_put_operations_maintain_secrets(self, client, temp_settings_setup):
        """Test that multiple PUT operations properly maintain secret values"""
        # First update: change non-secret, preserve secrets
        response1 = client.put("/api/v1/settings/", json={
            "PROJECT_NAME": "First Update",
            "KUCOIN_API_KEY": "",  # Preserve
            "DEBUG": True
        })
        assert response1.status_code == 200
        
        # Second update: change different non-secret, preserve secrets
        response2 = client.put("/api/v1/settings/", json={
            "KUCOIN_SANDBOX": True,
            "KUCOIN_API_SECRET": "***",  # Preserve
            "DEBUG": False
        })
        assert response2.status_code == 200
        
        # Third update: actually change one secret
        response3 = client.put("/api/v1/settings/", json={
            "KUCOIN_API_PASSPHRASE": "new_passphrase_123",
            "POSTGRES_PASSWORD": "",  # Preserve
        })
        assert response3.status_code == 200
        
        # Check final state
        file_data = settings_manager._load_file_settings()
        
        # Original secrets should be preserved
        assert file_data['KUCOIN_API_KEY'] == "existing_api_key_123"
        assert file_data['KUCOIN_API_SECRET'] == "existing_secret_456" 
        assert file_data['POSTGRES_PASSWORD'] == "existing_db_pass"
        
        # Updated secret should be changed
        assert file_data['KUCOIN_API_PASSPHRASE'] == "new_passphrase_123"
        
        # Latest non-secret changes should be applied
        assert file_data['PROJECT_NAME'] == "First Update"
        assert file_data['KUCOIN_SANDBOX'] is True
        assert file_data['DEBUG'] is False
    
    def test_get_after_put_always_shows_masked_secrets(self, client, temp_settings_setup):
        """Test that GET always shows masked secrets even after PUT updates"""
        # Update with new secret
        client.put("/api/v1/settings/", json={
            "KUCOIN_API_KEY": "brand_new_secret_key_123",
            "PROJECT_NAME": "Updated via PUT"
        })
        
        # GET should still mask the secret
        response = client.get("/api/v1/settings/")
        assert response.status_code == 200
        
        data = response.json()
        assert data['KUCOIN_API_KEY'] == "***"  # Should be masked
        assert data['PROJECT_NAME'] == "Updated via PUT"  # Should show updated value
        
        # Verify the actual secret was stored (by checking file directly)
        file_data = settings_manager._load_file_settings()
        assert file_data['KUCOIN_API_KEY'] == "brand_new_secret_key_123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
