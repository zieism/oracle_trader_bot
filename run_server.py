# run_server.py - Development server runner
"""
Simple script to start the FastAPI server for development and testing
"""
import uvicorn
import os
import sys

# Ensure the app module is in the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'oracle_trader_bot'))

if __name__ == "__main__":
    print("Starting Oracle Trader Bot API Server...")
    print("Server will be available at: http://localhost:8000 (configurable via settings.API_INTERNAL_BASE_URL)")
    print("API documentation: http://localhost:8000/docs (configurable via settings.API_INTERNAL_BASE_URL)")
    print("Health check: http://localhost:8000/api/health (configurable via settings.API_INTERNAL_BASE_URL)")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["oracle_trader_bot"],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)
