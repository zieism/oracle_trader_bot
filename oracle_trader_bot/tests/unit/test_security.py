# tests/unit/test_security.py
import pytest
from app.security.encryption import encryption_manager


class TestEncryptionManager:
    """Unit tests for Encryption Manager."""
    
    def test_initialize_encryption(self):
        """Test encryption initialization."""
        result = encryption_manager.initialize_encryption("test_password_2024")
        assert result is True
    
    def test_encrypt_decrypt_data(self):
        """Test basic data encryption and decryption."""
        encryption_manager.initialize_encryption("test_password_2024")
        
        original_data = "sensitive_api_key_12345"
        
        # Encrypt data
        encrypted_data = encryption_manager.encrypt_data(original_data)
        assert encrypted_data is not None
        assert encrypted_data != original_data
        assert len(encrypted_data) > len(original_data)
        
        # Decrypt data
        decrypted_data = encryption_manager.decrypt_data(encrypted_data)
        assert decrypted_data == original_data
    
    def test_encrypt_decrypt_api_credentials(self):
        """Test API credentials encryption and decryption."""
        encryption_manager.initialize_encryption("test_password_2024")
        
        api_key = "test_api_key_123"
        api_secret = "test_api_secret_456"
        passphrase = "test_passphrase_789"
        
        # Encrypt credentials
        encrypted_creds = encryption_manager.encrypt_api_credentials(
            api_key, api_secret, passphrase
        )
        
        assert encrypted_creds is not None
        assert "encrypted_api_key" in encrypted_creds
        assert "encrypted_api_secret" in encrypted_creds
        assert "encrypted_passphrase" in encrypted_creds
        
        # Decrypt credentials
        decrypted_creds = encryption_manager.decrypt_api_credentials(encrypted_creds)
        
        assert decrypted_creds is not None
        decrypted_key, decrypted_secret, decrypted_passphrase = decrypted_creds
        
        assert decrypted_key == api_key
        assert decrypted_secret == api_secret
        assert decrypted_passphrase == passphrase
    
    def test_is_encrypted_format(self):
        """Test encrypted format detection."""
        encryption_manager.initialize_encryption("test_password_2024")
        
        # Plain text should not be detected as encrypted
        assert encryption_manager.is_encrypted_format("plain_text") is False
        assert encryption_manager.is_encrypted_format("short") is False
        
        # Encrypted data should be detected
        encrypted_data = encryption_manager.encrypt_data("test_data")
        assert encryption_manager.is_encrypted_format(encrypted_data) is True
    
    def test_encryption_without_initialization(self):
        """Test encryption operations without proper initialization."""
        # Create new instance to test auto-initialization
        from app.security.encryption import EncryptionManager
        new_manager = EncryptionManager()
        
        # Should auto-initialize and work
        encrypted_data = new_manager.encrypt_data("test_data")
        assert encrypted_data is not None
        
        decrypted_data = new_manager.decrypt_data(encrypted_data)
        assert decrypted_data == "test_data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])