# tests/test_settings_security.py
"""
Unit tests for enhanced settings security features:
- Secret masking on GET
- Secret preservation on PUT with empty/*** values
- Optional encryption round-trip
- Secure file permissions
"""

import pytest
import os
import json
import tempfile
import stat
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "oracle_trader_bot"))

from app.crud.crud_settings import SettingsManager
from app.schemas.settings import SettingsUpdate
from app.utils.crypto_helper import SettingsEncryption
from app.core.config import settings


@pytest.fixture
def temp_settings_manager():
    """Create settings manager with temporary directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SettingsManager()
        manager.runtime_dir = Path(temp_dir) / ".runtime"
        manager.settings_file = manager.runtime_dir / "settings.json"
        manager._ensure_runtime_dir()
        yield manager

@pytest.fixture
def sample_settings_data():
    """Sample settings data with secrets"""
    return {
        'PROJECT_NAME': 'Test Project',
        'VERSION': '1.0.0',
        'DEBUG': True,
        'KUCOIN_API_KEY': 'test_api_key_123',
        'KUCOIN_API_SECRET': 'test_secret_456',
        'KUCOIN_API_PASSPHRASE': 'test_pass_789',
        'POSTGRES_PASSWORD': 'db_password_abc',
        'KUCOIN_SANDBOX': True,
        'SERVER_PUBLIC_IP': '127.0.0.1'
    }


class TestSettingsSecurity:
    """Test settings security enhancements"""
    
    def test_secret_masking_always_applied(self, temp_settings_manager, sample_settings_data):
        """Test that secrets are ALWAYS masked in GET responses, regardless of actual values"""
        manager = temp_settings_manager
        
        # Test with actual secret values
        masked = manager._mask_secrets(sample_settings_data)
        
        assert masked['KUCOIN_API_KEY'] == "***"
        assert masked['KUCOIN_API_SECRET'] == "***"
        assert masked['KUCOIN_API_PASSPHRASE'] == "***"
        assert masked['POSTGRES_PASSWORD'] == "***"
        
        # Non-secret fields should remain unchanged
        assert masked['PROJECT_NAME'] == 'Test Project'
        assert masked['KUCOIN_SANDBOX'] is True
        
        # Test with empty secrets - should still be masked
        empty_secrets = sample_settings_data.copy()
        empty_secrets.update({
            'KUCOIN_API_KEY': '',
            'KUCOIN_API_SECRET': None,
            'POSTGRES_PASSWORD': '   '  # whitespace
        })
        
        masked_empty = manager._mask_secrets(empty_secrets)
        assert masked_empty['KUCOIN_API_KEY'] == "***"
        assert masked_empty['KUCOIN_API_SECRET'] == "***"  # None becomes ***
        assert masked_empty['POSTGRES_PASSWORD'] == "***"
    
    def test_secret_preservation_on_put(self, temp_settings_manager, sample_settings_data):
        """Test that existing secrets are preserved when PUT contains empty/*** values"""
        manager = temp_settings_manager
        
        # Simulate existing stored settings
        existing_settings = sample_settings_data.copy()
        
        # Test updates with various empty/masked values
        updates = {
            'KUCOIN_API_KEY': '',  # Empty string - should preserve existing
            'KUCOIN_API_SECRET': '   ',  # Whitespace - should preserve existing
            'KUCOIN_API_PASSPHRASE': '***',  # Masked - should preserve existing
            'POSTGRES_PASSWORD': 'new_password',  # Valid new value - should update
            'PROJECT_NAME': 'Updated Project'  # Non-secret - should update
        }
        
        preserved = manager._preserve_existing_secrets(updates, existing_settings)
        
        # Existing secrets should be preserved
        assert preserved['KUCOIN_API_KEY'] == 'test_api_key_123'
        assert preserved['KUCOIN_API_SECRET'] == 'test_secret_456'
        assert preserved['KUCOIN_API_PASSPHRASE'] == 'test_pass_789'
        
        # New valid secret should be updated
        assert preserved['POSTGRES_PASSWORD'] == 'new_password'
        
        # Non-secrets should be updated normally
        assert preserved['PROJECT_NAME'] == 'Updated Project'
    
    def test_secret_preservation_no_existing(self, temp_settings_manager):
        """Test secret preservation when no existing values exist"""
        manager = temp_settings_manager
        
        updates = {
            'KUCOIN_API_KEY': '',  # Empty with no existing
            'KUCOIN_API_SECRET': '***',  # Masked with no existing
            'PROJECT_NAME': 'New Project'
        }
        
        preserved = manager._preserve_existing_secrets(updates, {})
        
        # Empty secrets with no existing should be removed from updates
        assert 'KUCOIN_API_KEY' not in preserved
        assert 'KUCOIN_API_SECRET' not in preserved
        
        # Non-secrets should remain
        assert preserved['PROJECT_NAME'] == 'New Project'
    
    def test_secret_format_validation(self, temp_settings_manager):
        """Test secret format validation without leaking values"""
        manager = temp_settings_manager
        
        # Valid secrets
        valid, error = manager._validate_secret_format('KUCOIN_API_KEY', 'valid_key_123')
        assert valid is True
        assert error is None
        
        # Too short
        valid, error = manager._validate_secret_format('KUCOIN_API_KEY', 'short')
        assert valid is False
        assert "at least 8 characters" in error
        
        # Invalid characters (but don't leak the actual value in error)
        valid, error = manager._validate_secret_format('KUCOIN_API_KEY', 'invalid@chars!')
        assert valid is False
        assert "invalid characters" in error
        assert 'invalid@chars!' not in error  # Should not leak actual value
        
        # Empty should be valid (will be ignored)
        valid, error = manager._validate_secret_format('KUCOIN_API_KEY', '')
        assert valid is True
        assert error is None
    
    def test_redacted_logging(self, temp_settings_manager, sample_settings_data):
        """Test that sensitive data is redacted in logging"""
        manager = temp_settings_manager
        
        redacted = manager._redact_for_logging(sample_settings_data)
        
        # Secrets should be redacted
        assert redacted['KUCOIN_API_KEY'] == '<redacted>'
        assert redacted['KUCOIN_API_SECRET'] == '<redacted>'
        assert redacted['POSTGRES_PASSWORD'] == '<redacted>'
        
        # Non-secrets should remain
        assert redacted['PROJECT_NAME'] == 'Test Project'
        assert redacted['KUCOIN_SANDBOX'] is True
    
    def test_file_permissions_security(self, temp_settings_manager):
        """Test that runtime directory and settings file have secure permissions"""
        manager = temp_settings_manager
        
        if os.name == 'posix':  # Only test on Unix-like systems
            # Check runtime directory permissions
            dir_stat = manager.runtime_dir.stat()
            dir_mode = stat.filemode(dir_stat.st_mode)
            # Should be drwx------ (0o700)
            assert dir_stat.st_mode & 0o777 == 0o700
            
            # Save a file and check its permissions
            test_data = {'test': 'data'}
            success = manager._save_file_settings(test_data)
            assert success is True
            
            # Check file permissions
            file_stat = manager.settings_file.stat()
            # Should be -rw------- (0o600)
            assert file_stat.st_mode & 0o777 == 0o600
    
    def test_atomic_file_operations(self, temp_settings_manager, sample_settings_data):
        """Test that file operations are atomic (temp file -> rename)"""
        manager = temp_settings_manager
        
        # Save should succeed
        success = manager._save_file_settings(sample_settings_data)
        assert success is True
        
        # Settings file should exist
        assert manager.settings_file.exists()
        
        # Temp file should not exist after successful operation
        temp_file = manager.settings_file.with_suffix('.tmp')
        assert not temp_file.exists()
        
        # File should contain the data
        loaded = manager._load_file_settings()
        assert loaded is not None
        assert loaded['PROJECT_NAME'] == sample_settings_data['PROJECT_NAME']


class TestSettingsEncryption:
    """Test optional encryption features"""
    
    @pytest.fixture
    def encryption_with_key(self):
        """Create encryption helper with test key"""
        with patch.dict(os.environ, {'SETTINGS_ENCRYPTION_KEY': 'test_key_for_encryption'}):
            return SettingsEncryption()
    
    @pytest.fixture
    def encryption_without_key(self):
        """Create encryption helper without key"""
        with patch.dict(os.environ, {}, clear=False):
            # Remove the key if it exists
            if 'SETTINGS_ENCRYPTION_KEY' in os.environ:
                del os.environ['SETTINGS_ENCRYPTION_KEY']
            return SettingsEncryption()
    
    def test_encryption_key_detection(self):
        """Test encryption key detection from environment"""
        # Without key
        with patch.dict(os.environ, {}, clear=False):
            if 'SETTINGS_ENCRYPTION_KEY' in os.environ:
                del os.environ['SETTINGS_ENCRYPTION_KEY']
            enc = SettingsEncryption()
            assert not enc.is_enabled()
        
        # With key
        with patch.dict(os.environ, {'SETTINGS_ENCRYPTION_KEY': 'test_key'}):
            enc = SettingsEncryption()
            assert enc.is_enabled()
    
    def test_encryption_round_trip(self, encryption_with_key):
        """Test encryption/decryption round-trip maintains data integrity"""
        enc = encryption_with_key
        
        test_data = {
            'string': 'test_value',
            'integer': 42,
            'boolean': True,
            'list': [1, 2, 3],
            'nested': {'inner': 'value'},
            'secret': 'sensitive_data_123'
        }
        
        # Encrypt and decrypt
        encrypted = enc.encrypt_to_base64(test_data)
        decrypted = enc.decrypt_from_base64(encrypted)
        
        # Data should be identical
        assert decrypted == test_data
        
        # Encrypted data should be different
        assert encrypted != json.dumps(test_data)
        assert len(encrypted) > 0
    
    def test_encryption_without_key_fails(self, encryption_without_key):
        """Test that encryption operations fail gracefully without key"""
        enc = encryption_without_key
        
        test_data = {'test': 'data'}
        
        with pytest.raises(ValueError, match="Encryption not available"):
            enc.encrypt_to_base64(test_data)
        
        with pytest.raises((ValueError, Exception)):  # Could be ValueError or base64 error
            enc.decrypt_from_base64("fake_encrypted_data")
    
    def test_encryption_round_trip_test_method(self, encryption_with_key, encryption_without_key):
        """Test the built-in round-trip test method"""
        # With key should succeed
        enc_with_key = encryption_with_key
        success, error = enc_with_key.test_round_trip()
        assert success is True
        assert error is None
        
        # Without key should fail gracefully
        enc_without_key = encryption_without_key
        success, error = enc_without_key.test_round_trip()
        assert success is False
        assert "not enabled" in error
    
    def test_invalid_encrypted_data_handling(self, encryption_with_key):
        """Test handling of invalid encrypted data"""
        enc = encryption_with_key
        
        # Too short data
        with pytest.raises(ValueError, match="too short"):
            enc.decrypt_data(b"short")
        
        # Invalid base64
        with pytest.raises(Exception):  # Various exceptions possible
            enc.decrypt_from_base64("invalid_base64_data!")
    
    def test_settings_manager_encryption_integration(self, temp_settings_manager, sample_settings_data):
        """Test settings manager integration with encryption"""
        manager = temp_settings_manager
        
        # Test with encryption enabled
        with patch.dict(os.environ, {'SETTINGS_ENCRYPTION_KEY': 'test_encryption_key'}):
            # Create new encryption instance with the key
            from app.utils.crypto_helper import SettingsEncryption
            test_encryption = SettingsEncryption()
            
            # Patch both the module instance and the import in crud_settings
            with patch('app.utils.crypto_helper.settings_encryption', test_encryption):
                with patch('app.crud.crud_settings.settings_encryption', test_encryption):
                    # Save settings
                    success = manager._save_file_settings(sample_settings_data)
                    assert success is True
                    
                    # File should exist and not be plain JSON
                    content = manager.settings_file.read_text()
                    
                    # Should not be readable as plain JSON
                    with pytest.raises(json.JSONDecodeError):
                        json.loads(content)
                    
                    # Should be loadable through manager
                    loaded = manager._load_file_settings()
                    assert loaded is not None
                    assert loaded['PROJECT_NAME'] == sample_settings_data['PROJECT_NAME']
    
    def test_fallback_to_plaintext_without_key(self, temp_settings_manager, sample_settings_data):
        """Test that settings fall back to plaintext without encryption key"""
        manager = temp_settings_manager
        
        # Ensure no encryption key
        with patch.dict(os.environ, {}, clear=False):
            if 'SETTINGS_ENCRYPTION_KEY' in os.environ:
                del os.environ['SETTINGS_ENCRYPTION_KEY']
            
            # Create new encryption instance without key
            from app.utils.crypto_helper import SettingsEncryption
            test_encryption = SettingsEncryption()
            
            # Patch both the module instance and the import in crud_settings
            with patch('app.utils.crypto_helper.settings_encryption', test_encryption):
                with patch('app.crud.crud_settings.settings_encryption', test_encryption):
                    # Save settings
                    success = manager._save_file_settings(sample_settings_data)
                    assert success is True
                    
                    # File should be readable as plain JSON
                    content = manager.settings_file.read_text()
                    data = json.loads(content)  # Should not raise
                    assert data['PROJECT_NAME'] == sample_settings_data['PROJECT_NAME']
                    
                    # Should be loadable through manager
                    loaded = manager._load_file_settings()
                    assert loaded is not None
                    assert loaded['PROJECT_NAME'] == sample_settings_data['PROJECT_NAME']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
