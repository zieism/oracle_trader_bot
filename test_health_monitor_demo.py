#!/usr/bin/env python3
"""
Health Monitor Test Script

Simple test script to verify the health monitoring functionality.
Runs the health monitor against a test server to demonstrate functionality.
"""

import asyncio
import subprocess
import sys
import time
import os
from pathlib import Path

def run_health_monitor_demo():
    """Run health monitor demo against test server"""
    
    print("🏥 Oracle Trader Bot - Health Monitor Demo")
    print("=" * 50)
    print()
    
    # Start the simple test server in background
    print("🚀 Starting test server...")
    server_process = None
    
    try:
        # Set environment variables for CORS testing
        env = os.environ.copy()
        env["FRONTEND_ORIGINS"] = "http://localhost:5173,https://oracletrader.app,https://www.oracletrader.app"
        
        # Start server
        server_process = subprocess.Popen([
            sys.executable, "simple_test_server.py"
        ], env=env)
        
        # Wait for server to start
        print("⏳ Waiting for server to start...")
        time.sleep(3)
        
        print("✅ Test server started")
        print()
        
        # Run health monitor
        print("🔍 Running health monitor...")
        print("-" * 30)
        
        result = subprocess.run([
            sys.executable, "health_monitor.py",
            "--url", "http://localhost:8000",
            "--verbose"
        ])
        
        print()
        print("-" * 30)
        
        if result.returncode == 0:
            print("✅ Health monitor completed successfully!")
        else:
            print("❌ Health monitor detected issues")
        
        print()
        print("📊 Testing JSON output...")
        print("-" * 30)
        
        # Test JSON output
        result = subprocess.run([
            sys.executable, "health_monitor.py", 
            "--url", "http://localhost:8000",
            "--json"
        ], capture_output=True, text=True)
        
        if result.stdout:
            print("JSON Output Preview:")
            lines = result.stdout.split('\n')[:10]  # First 10 lines
            for line in lines:
                if line.strip():
                    print(f"  {line}")
            if len(result.stdout.split('\n')) > 10:
                print("  ...")
        
        print()
        print("🎉 Health monitor demo completed!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        # Clean up server process
        if server_process:
            print("\n🛑 Stopping test server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
                print("✅ Test server stopped")
            except subprocess.TimeoutExpired:
                print("⏰ Force killing test server...")
                server_process.kill()

def main():
    """Main demo function"""
    script_dir = Path(__file__).parent
    
    # Check if required files exist
    required_files = [
        "health_monitor.py", 
        "simple_test_server.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not (script_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   • {file}")
        print("\nPlease ensure all files are present before running the demo.")
        return 1
    
    print("📋 Health Monitor Demo")
    print("This demo will:")
    print("  1. Start a test server on http://localhost:8000")
    print("  2. Run health monitor against the test server") 
    print("  3. Display both human-readable and JSON output")
    print("  4. Clean up the test server")
    print()
    
    try:
        run_health_monitor_demo()
        return 0
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
