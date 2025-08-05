# app/security/encryption.py
import logging
import os
import base64
from typing import Optional, Tuple, Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Manages encryption and decryption of sensitive data like API keys.
    Uses symmetric encryption with password-based key derivation.
    """
    
    def __init__(self):
        self.logger = logger
        self._cipher_suite: Optional[Fernet] = None
        self._encryption_key: Optional[bytes] = None
        
    def _generate_key_from_password(self, password: str, salt: bytes) -> bytes:
        """Generate encryption key from password and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def initialize_encryption(self, master_password: Optional[str] = None) -> bool:
        """
        Initialize encryption with master password.
        
        Args:
            master_password: Master password for encryption. If None, uses environment variable.
            
        Returns:
            True if successful
        """
        try:
            # Get master password from environment or parameter
            password = master_password or os.getenv('MASTER_PASSWORD', 'default_oracle_trader_key_2024')
            
            # Use a fixed salt for consistency (in production, this should be stored securely)
            salt = b'oracle_trader_salt_2024'[:16].ljust(16, b'0')
            
            # Generate encryption key
            self._encryption_key = self._generate_key_from_password(password, salt)
            self._cipher_suite = Fernet(self._encryption_key)
            
            self.logger.info("Encryption manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing encryption: {e}")
            return False
    
    def encrypt_data(self, data: str) -> Optional[str]:
        """
        Encrypt string data.
        
        Args:
            data: String to encrypt
            
        Returns:
            Base64 encoded encrypted data or None if error
        """
        try:
            if not self._cipher_suite:
                if not self.initialize_encryption():
                    return None
            
            encrypted_data = self._cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            self.logger.error(f"Error encrypting data: {e}")
            return None
    
    def decrypt_data(self, encrypted_data: str) -> Optional[str]:
        """
        Decrypt string data.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted string or None if error
        """
        try:
            if not self._cipher_suite:
                if not self.initialize_encryption():
                    return None
            
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._cipher_suite.decrypt(encrypted_bytes)
            return decrypted_data.decode()
            
        except Exception as e:
            self.logger.error(f"Error decrypting data: {e}")
            return None
    
    def encrypt_api_credentials(self, api_key: str, api_secret: str, passphrase: str = "") -> Optional[Dict[str, str]]:
        """
        Encrypt API credentials.
        
        Args:
            api_key: API key to encrypt
            api_secret: API secret to encrypt
            passphrase: API passphrase to encrypt
            
        Returns:
            Dictionary with encrypted credentials or None if error
        """
        try:
            encrypted_key = self.encrypt_data(api_key)
            encrypted_secret = self.encrypt_data(api_secret)
            encrypted_passphrase = self.encrypt_data(passphrase) if passphrase else ""
            
            if encrypted_key and encrypted_secret:
                return {
                    "encrypted_api_key": encrypted_key,
                    "encrypted_api_secret": encrypted_secret,
                    "encrypted_passphrase": encrypted_passphrase
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error encrypting API credentials: {e}")
            return None
    
    def decrypt_api_credentials(self, encrypted_credentials: Dict[str, str]) -> Optional[Tuple[str, str, str]]:
        """
        Decrypt API credentials.
        
        Args:
            encrypted_credentials: Dictionary with encrypted credentials
            
        Returns:
            Tuple of (api_key, api_secret, passphrase) or None if error
        """
        try:
            api_key = self.decrypt_data(encrypted_credentials.get("encrypted_api_key", ""))
            api_secret = self.decrypt_data(encrypted_credentials.get("encrypted_api_secret", ""))
            passphrase = self.decrypt_data(encrypted_credentials.get("encrypted_passphrase", "")) or ""
            
            if api_key and api_secret:
                return api_key, api_secret, passphrase
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error decrypting API credentials: {e}")
            return None
    
    def is_encrypted_format(self, data: str) -> bool:
        """Check if data appears to be in encrypted format."""
        try:
            # Encrypted data should be base64 encoded and reasonably long
            if len(data) < 20:
                return False
            
            # Try to decode as base64
            base64.urlsafe_b64decode(data.encode())
            return True
            
        except Exception:
            return False


# Global instance
encryption_manager = EncryptionManager()