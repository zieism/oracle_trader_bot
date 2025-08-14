# app/utils/crypto_helper.py
"""
Simple AES-GCM encryption helper for settings file protection.

Provides optional at-rest encryption for file-backed settings in lite mode.
Uses AES-256-GCM with PBKDF2 key derivation from environment key.
"""

import os
import base64
import json
from typing import Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class SettingsEncryption:
    """Simple AES-GCM encryption for settings files"""
    
    def __init__(self):
        self.key = self._get_encryption_key()
        self.enabled = self.key is not None
    
    def _get_encryption_key(self) -> Optional[bytes]:
        """Get encryption key from environment variable"""
        env_key = os.getenv('SETTINGS_ENCRYPTION_KEY')
        if not env_key or not env_key.strip():
            return None
        
        # Derive 32-byte key from environment string using PBKDF2
        # Use a fixed salt for consistency (in production, consider unique per installation)
        salt = b'oracle_trader_settings_salt_v1'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(env_key.encode('utf-8'))
    
    def is_enabled(self) -> bool:
        """Check if encryption is enabled"""
        return self.enabled
    
    def encrypt_data(self, data: Dict[str, Any]) -> bytes:
        """
        Encrypt settings dictionary to bytes
        
        Returns:
            Encrypted data as bytes (nonce + ciphertext)
        """
        if not self.enabled:
            raise ValueError("Encryption not available - SETTINGS_ENCRYPTION_KEY not set")
        
        # Serialize to JSON
        json_data = json.dumps(data, default=str, separators=(',', ':')).encode('utf-8')
        
        # Generate random nonce
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        
        # Encrypt
        aesgcm = AESGCM(self.key)
        ciphertext = aesgcm.encrypt(nonce, json_data, None)
        
        # Combine nonce + ciphertext
        encrypted_data = nonce + ciphertext
        
        logger.debug(f"Encrypted settings data: {len(json_data)} bytes -> {len(encrypted_data)} bytes")
        return encrypted_data
    
    def decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """
        Decrypt bytes back to settings dictionary
        
        Args:
            encrypted_data: Bytes containing nonce + ciphertext
            
        Returns:
            Decrypted settings dictionary
        """
        if not self.enabled:
            raise ValueError("Encryption not available - SETTINGS_ENCRYPTION_KEY not set")
        
        if len(encrypted_data) < 12:
            raise ValueError("Invalid encrypted data - too short")
        
        # Split nonce and ciphertext
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        # Decrypt
        aesgcm = AESGCM(self.key)
        json_data = aesgcm.decrypt(nonce, ciphertext, None)
        
        # Parse JSON
        data = json.loads(json_data.decode('utf-8'))
        
        logger.debug(f"Decrypted settings data: {len(encrypted_data)} bytes -> {len(json_data)} bytes")
        return data
    
    def encrypt_to_base64(self, data: Dict[str, Any]) -> str:
        """Encrypt and encode as base64 string for file storage"""
        encrypted_bytes = self.encrypt_data(data)
        return base64.b64encode(encrypted_bytes).decode('ascii')
    
    def decrypt_from_base64(self, encoded_data: str) -> Dict[str, Any]:
        """Decrypt from base64-encoded string"""
        encrypted_bytes = base64.b64decode(encoded_data.encode('ascii'))
        return self.decrypt_data(encrypted_bytes)
    
    def test_round_trip(self) -> Tuple[bool, Optional[str]]:
        """
        Test encryption/decryption round-trip
        
        Returns:
            (success, error_message)
        """
        if not self.enabled:
            return False, "Encryption not enabled"
        
        try:
            # Test data
            test_data = {
                'test_key': 'test_value',
                'secret': 'sensitive_data_123',
                'number': 42,
                'boolean': True,
                'list': [1, 2, 3],
                'nested': {'inner': 'value'}
            }
            
            # Encrypt and decrypt
            encrypted = self.encrypt_to_base64(test_data)
            decrypted = self.decrypt_from_base64(encrypted)
            
            # Verify data integrity
            if decrypted == test_data:
                return True, None
            else:
                return False, "Data mismatch after round-trip"
                
        except Exception as e:
            return False, str(e)

# Global instance
settings_encryption = SettingsEncryption()
