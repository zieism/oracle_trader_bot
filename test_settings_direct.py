#!/usr/bin/env python3
# Direct settings test - no server required
import sys
import os
import asyncio

# Add the project root to the Python path  
sys.path.append(os.path.join(os.path.dirname(__file__), 'oracle_trader_bot'))
os.chdir('oracle_trader_bot')

from app.crud.crud_settings import settings_manager
from app.schemas.settings import SettingsUpdate

async def test_settings_manager():
    """Test settings manager directly"""
    print("🧪 Testing Settings Manager (Direct)")
    print("=" * 50)
    
    try:
        # Test GET settings
        print("1. Testing get_settings()...")
        settings = await settings_manager.get_settings()
        print("✅ GET settings - SUCCESS")
        
        # Check that secrets are masked
        secret_fields = ['KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_API_PASSPHRASE', 'POSTGRES_PASSWORD']
        for field in secret_fields:
            value = getattr(settings, field, None)
            if value and value != '***':
                print(f"⚠️  Secret field {field} is not masked: {value}")
            else:
                print(f"✅ Secret field {field} is properly masked")
        
        # Test UPDATE settings
        print("\n2. Testing update_settings()...")
        update = SettingsUpdate(
            DEBUG=not settings.DEBUG,
            CANDLE_LIMIT_BOT=150,
            PROJECT_NAME="Oracle Trader Bot - Test"
        )
        
        updated_settings = await settings_manager.update_settings(update)
        print("✅ UPDATE settings - SUCCESS")
        
        # Verify changes
        if updated_settings.DEBUG != settings.DEBUG:
            print("✅ DEBUG setting updated correctly")
        else:
            print("❌ DEBUG setting not updated")
            
        if updated_settings.CANDLE_LIMIT_BOT == 150:
            print("✅ CANDLE_LIMIT_BOT setting updated correctly")
        else:
            print(f"❌ CANDLE_LIMIT_BOT not updated: {updated_settings.CANDLE_LIMIT_BOT}")
            
        # Test file persistence in lite mode
        print("\n3. Testing file persistence...")
        settings_file = ".runtime/settings.json"
        if os.path.exists(settings_file):
            print("✅ Settings file created")
            import json
            try:
                with open(settings_file, 'r') as f:
                    file_data = json.load(f)
                    if file_data.get("CANDLE_LIMIT_BOT") == 150:
                        print("✅ Settings properly persisted to file")
                    else:
                        print("⚠️  Settings may not be properly persisted")
            except Exception as e:
                print(f"⚠️  Error reading settings file: {e}")
        else:
            print("⚠️  Settings file not found")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_settings_manager())
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Settings manager test PASSED!")
    else:
        print("❌ Settings manager test FAILED!")
        sys.exit(1)
