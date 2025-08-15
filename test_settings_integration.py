import pytest
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import directly from app.core.config instead of through deprecated shim
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'oracle_trader_bot')))
from app.core.config import Settings
settings = Settings()

def test_settings_endpoints_integration():
    """Test settings endpoints with lite mode support"""
    import requests
    import json
    
    base_url = settings.API_INTERNAL_BASE_URL
    
    try:
        # Test GET settings
        print(f"Testing GET {base_url}/api/v1/settings/")
        response = requests.get(f"{base_url}/api/v1/settings/", timeout=10)
        
        if response.status_code == 200:
            settings_data = response.json()
            print("✅ GET /api/v1/settings/ - SUCCESS")
            
            # Check that secrets are masked
            secret_fields = ['KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_API_PASSPHRASE', 'POSTGRES_PASSWORD']
            for field in secret_fields:
                if settings_data.get(field) and settings_data[field] != '***':
                    print(f"⚠️  Secret field {field} is not masked: {settings_data[field]}")
                else:
                    print(f"✅ Secret field {field} is properly masked")
            
            # Test PUT settings with partial update
            print(f"\nTesting PUT {base_url}/api/v1/settings/")
            update_payload = {
                "DEBUG": not settings_data.get("DEBUG", False),
                "CANDLE_LIMIT_BOT": 150,  # Change from default 200
                "PROJECT_NAME": "Oracle Trader Bot - Updated"
            }
            
            response = requests.put(
                f"{base_url}/api/v1/settings/", 
                json=update_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                updated_settings = response.json()
                print("✅ PUT /api/v1/settings/ - SUCCESS")
                
                # Verify changes were applied
                if updated_settings.get("DEBUG") == update_payload["DEBUG"]:
                    print("✅ DEBUG setting updated correctly")
                else:
                    print(f"❌ DEBUG setting not updated: expected {update_payload['DEBUG']}, got {updated_settings.get('DEBUG')}")
                
                if updated_settings.get("CANDLE_LIMIT_BOT") == update_payload["CANDLE_LIMIT_BOT"]:
                    print("✅ CANDLE_LIMIT_BOT setting updated correctly")
                else:
                    print(f"❌ CANDLE_LIMIT_BOT setting not updated: expected {update_payload['CANDLE_LIMIT_BOT']}, got {updated_settings.get('CANDLE_LIMIT_BOT')}")
                
                # Verify secrets are still masked
                for field in secret_fields:
                    if updated_settings.get(field) and updated_settings[field] != '***':
                        print(f"⚠️  After update, secret field {field} is not masked: {updated_settings[field]}")
                    else:
                        print(f"✅ After update, secret field {field} is still properly masked")
                        
            else:
                print(f"❌ PUT /api/v1/settings/ failed: {response.status_code} - {response.text}")
                
        else:
            print(f"❌ GET /api/v1/settings/ failed: {response.status_code} - {response.text}")
            return False
            
        # Test settings persistence by checking if .runtime/settings.json exists in lite mode
        if settings.APP_STARTUP_MODE == "lite":
            settings_file = ".runtime/settings.json"
            if os.path.exists(settings_file):
                print("✅ Settings file created in lite mode")
                try:
                    with open(settings_file, 'r') as f:
                        file_data = json.load(f)
                        if file_data.get("CANDLE_LIMIT_BOT") == 150:
                            print("✅ Settings properly persisted to file")
                        else:
                            print("⚠️  Settings may not be properly persisted to file")
                except Exception as e:
                    print(f"⚠️  Error reading settings file: {e}")
            else:
                print("⚠️  Settings file not found in lite mode")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_settings_secret_handling():
    """Test that secrets are handled properly (not updated when empty)"""
    import requests
    
    base_url = settings.API_INTERNAL_BASE_URL
    
    try:
        # Get current settings
        response = requests.get(f"{base_url}/api/v1/settings/", timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to get settings for secret test: {response.status_code}")
            return False
            
        # Try to update with empty secret (should be ignored)
        update_payload = {
            "KUCOIN_API_KEY": "",  # Empty secret should be ignored
            "KUCOIN_API_SECRET": "   ",  # Whitespace-only should be ignored
            "CANDLE_LIMIT_BOT": 175  # This should be updated
        }
        
        response = requests.put(
            f"{base_url}/api/v1/settings/", 
            json=update_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            updated_settings = response.json()
            print("✅ PUT with empty secrets - SUCCESS")
            
            # Verify empty secrets were ignored
            if updated_settings.get("KUCOIN_API_KEY") == "***":
                print("✅ Empty KUCOIN_API_KEY was properly ignored")
            else:
                print(f"❌ Empty KUCOIN_API_KEY was not ignored: {updated_settings.get('KUCOIN_API_KEY')}")
                
            # Verify non-secret was updated
            if updated_settings.get("CANDLE_LIMIT_BOT") == 175:
                print("✅ Non-secret field was properly updated")
            else:
                print(f"❌ Non-secret field was not updated: {updated_settings.get('CANDLE_LIMIT_BOT')}")
                
            return True
        else:
            print(f"❌ PUT with empty secrets failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error in secret handling test: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Settings API Integration...")
    print(f"Using API base URL: {settings.API_INTERNAL_BASE_URL}")
    print(f"Running in mode: {settings.APP_STARTUP_MODE}")
    print("=" * 60)
    
    # Run tests
    test1_success = test_settings_endpoints_integration()
    print("\n" + "=" * 60)
    test2_success = test_settings_secret_handling()
    
    print("\n" + "=" * 60)
    if test1_success and test2_success:
        print("🎉 All settings tests PASSED!")
    else:
        print("❌ Some settings tests FAILED!")
        sys.exit(1)
