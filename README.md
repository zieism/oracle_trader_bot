KuCoin Futures Automated Trader Bot
This project is an advanced automated trading bot for the KuCoin Futures market, developed using Python (FastAPI) for the backend and React (TypeScript) for the frontend. The bot is capable of technical analysis, executing trading strategies, managing risk, and providing a comprehensive user interface for monitoring and control.

Table of Contents
KuCoin Futures Automated Trader Bot

Table of Contents

Features

Technologies Used

Project Architecture

Getting Started

Prerequisites

Cloning the Repository

Backend Setup (Python/FastAPI)

Frontend Setup (React/TypeScript)

Nginx Configuration for Reverse Proxy and Basic Authentication

Running the Bot Engine

Using the Application

Troubleshooting

Future Enhancements

License

Features
Advanced Technical Analysis: Fetches market data, calculates indicators, and identifies market regimes (trending/ranging).

Trading Strategies: Implements Trend-Following and Range-Trading strategies capable of generating precise signals (including entry price, stop-loss, take-profit, and leverage).

Order Management: Sends market orders with initial stop-loss and take-profit to the KuCoin exchange.

Risk Management: Configurable trade amount per position and overall risk management.

PostgreSQL Database: Stores and tracks all open and closed trades, including detailed PNL and exit reasons.

Powerful FastAPI API: Provides RESTful endpoints for interacting with the bot, managing orders, and accessing database data.

React.js User Interface:

Comprehensive Dashboard: Displays overall bot status, USDT account balance, open positions (with real-time PNL details), and recent trades.

Dynamic Settings: Allows viewing and modifying bot parameters (e.g., trading symbols, leverage, trade amounts) directly from the UI.

Live Logs: View real-time server logs and bot analysis logs via WebSocket.

Bot Control: Start/Stop buttons to manage the bot's execution process.

Basic Security: Uses Nginx as a reverse proxy with Basic Authentication to protect public access.

Technologies Used
Backend:

Python 3.9+: Primary programming language.

FastAPI: High-performance web framework for building APIs.

SQLAlchemy: ORM for database interaction.

PostgreSQL: Relational database for storing bot data and trades.

CCXT: Library for interacting with the KuCoin Futures exchange.

Pandas & NumPy: For financial data analysis.

python-dotenv: For managing environment variables.

psutil: For managing the bot's process.

Frontend:

React.js (with Vite): JavaScript library for building user interfaces.

TypeScript: Superset of JavaScript for enhanced type safety and developer experience.

Material-UI (MUI): UI component library for a responsive and aesthetically pleasing design.

Axios: HTTP client for making API requests to the backend.

React Router DOM: For client-side routing in the Single Page Application (SPA).

Project Architecture
The project is divided into three main components:

Backend (FastAPI): This component is responsible for exposing APIs, interacting with the database, and managing the main bot process (start/stop).

Bot Engine (Python Script): This script contains the core trading logic. It runs as a separate process, fetches data from the exchange, performs analysis, generates signals, and manages orders. The backend is responsible for starting and stopping this process.

Frontend (React): This web-based user interface allows users to interact with the bot, monitor its status, change settings, and view logs.

Nginx acts as a Reverse Proxy, handling all incoming requests from the internet. It routes API-related requests to the backend (FastAPI) and UI-related requests to the frontend (React). This setup enhances security and simplifies port management.

Getting Started
This section guides you through the steps to install, configure, and run the trading bot on a new Linux server (Ubuntu Server recommended).

Prerequisites
Ensure your server has the following installed:

Operating System: Ubuntu Server 20.04 LTS or newer.

SSH Access: For connecting to your server.

Python 3.9+:

sudo apt update
sudo apt install python3.9 python3.9-venv python3-pip build-essential libpq-dev


PostgreSQL:

sudo apt install postgresql postgresql-contrib


Create a PostgreSQL user and database for the bot:

sudo -i -u postgres
createuser --interactive # Enter your desired database username (e.g., 'oracle_user')
createdb your_db_name # Enter your desired database name (e.g., 'oracle_db')
psql -d your_db_name -c "ALTER USER oracle_user WITH PASSWORD 'your_db_password';" # Set a strong password
exit


Node.js and npm/yarn:

sudo apt install curl
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g yarn # If you prefer yarn


Nginx:

sudo apt install nginx


Apache2-utils:

sudo apt install apache2-utils


Git:

sudo apt install git


Cloning the Repository
Connect to your new server via SSH:

ssh your_server_username@your_server_ip


(e.g., ssh root@150.241.85.30)

Create a project directory and clone the repository:

mkdir -p /root/oracle_trader_bot # Create the main project directory
cd /root/oracle_trader_bot
git clone your_repository_url . # The dot (.) means clone into the current directory


Backend Setup (Python/FastAPI)
Create and activate a Python virtual environment:

cd /root/oracle_trader_bot
python3.9 -m venv venv
source venv/bin/activate


Install Python dependencies:

pip install -r requirements.txt # Assumes you have a requirements.txt file
# If you don't have requirements.txt, install manually:
# pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg psycopg2-binary python-dotenv ccxt pandas numpy pydantic-settings aiohttp psutil


Configure the .env file:

Create or edit the .env file in the project root (/root/oracle_trader_bot/).

Enter your KuCoin API keys and PostgreSQL database credentials:

KUCOIN_API_KEY="YOUR_KUCOIN_API_KEY"
KUCOIN_API_SECRET="YOUR_KUCOIN_API_SECRET"
KUCOIN_API_PASSPHRASE="YOUR_KUCOIN_API_PASSPHRASE"
POSTGRES_SERVER="localhost"
POSTGRES_PORT="5432"
POSTGRES_USER="oracle_user" # Your database username created earlier
POSTGRES_PASSWORD="your_db_password" # Your database password set earlier
POSTGRES_DB="oracle_db" # Your database name created earlier
FIXED_USD_AMOUNT_PER_TRADE=2.0 # Set to 2.0 or higher to avoid InvalidOrder errors
# ... other bot settings


Run the FastAPI server:

cd /root/oracle_trader_bot/
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000


Note: Using 127.0.0.1 for host ensures FastAPI is only accessible internally by Nginx for security.

Frontend Setup (React/TypeScript)
Install Node.js dependencies:

cd /root/oracle_trader_bot/oracle-trader-frontend/
npm install # or yarn install


Adjust API URLs in src/services/apiService.ts:

Ensure your src/services/apiService.ts file exactly matches the code below. This change is crucial for the frontend to communicate with the backend via Nginx.

// src/services/apiService.ts
import axios from 'axios';

// Changed API_BASE_URL to a relative path. Nginx will proxy /api/ to the backend.
const API_BASE_URL = '/api/v1'; 
// Changed WS_BASE_URL to use window.location.host to dynamically get the current host (served by Nginx)
// This ensures WebSocket connections also go through Nginx.
const WS_BASE_URL = `ws://${window.location.host}/api/v1`; 

// ... rest of the code


Save the file.

Run the Vite development server:

cd /root/oracle_trader_bot/oracle-trader-frontend/
npm run dev -- --host 127.0.0.1 # or yarn dev --host 127.0.0.1


Note: Using 127.0.0.1 for host ensures Vite is only accessible internally by Nginx for security.

Nginx Configuration for Reverse Proxy and Basic Authentication
Create a password file for Nginx:

sudo htpasswd -c /etc/nginx/.htpasswd your_nginx_username # Replace with your desired Nginx username


Enter a strong password when prompted.

Create/Edit the Nginx configuration file:

Open the file /etc/nginx/sites-available/oracle_bot:

sudo nano /etc/nginx/sites-available/oracle_bot


Replace its content exactly with the code below (replace 150.241.85.30 with your actual server IP):

server {
    listen 80;
    server_name 150.241.85.30; # Replace with your server's public IP

    auth_basic "Restricted Access to Oracle Bot";
    auth_basic_user_file /etc/nginx/.htpasswd;

    # IMPORTANT: /api/ location MUST come BEFORE / location
    location /api/ {
        proxy_pass http://127.0.0.1:8000; # Proxy to your FastAPI backend (removed /api/ from target)
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300; 
        proxy_connect_timeout 300;
        proxy_send_timeout 300;

        # WebSocket proxy settings for /api/v1/ws/analysis-logs
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location / {
        proxy_pass http://127.0.0.1:5173; # Proxy to your React frontend
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300; 
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}


Save the file.

Enable the configuration and restart Nginx:

sudo ln -s /etc/nginx/sites-available/oracle_bot /etc/nginx/sites-enabled/
sudo nginx -t # Test Nginx configuration for syntax errors (should return "syntax is ok" and "test is successful")
sudo systemctl restart nginx


Running the Bot Engine
The bot engine (bot_engine.py) is managed by the FastAPI backend. Once FastAPI and the frontend are correctly running via Nginx, you can start the bot from the user interface (Dashboard page) by clicking the "Start Bot" button. This will launch the bot as a separate subprocess.

Using the Application
Access the User Interface: Open your web browser and navigate to http://150.241.85.30/.

Login: Enter the Nginx username and password you configured with htpasswd.

Dashboard: After logging in, you will see the bot's dashboard, displaying account information, open positions, and bot status.

Start/Stop Bot: Use the buttons on the dashboard to start or stop the bot.

Settings and Logs: Navigate to the "Bot Settings" and "Logs" sections in the menu to manage bot parameters and view system and analysis logs.

Troubleshooting
White Screen in Browser / CORS Errors:

Ensure your src/services/apiService.ts file in the frontend exactly matches the version provided in this README (using relative paths like /api/v1).

Ensure your Nginx configuration in /etc/nginx/sites-available/oracle_bot exactly matches the version provided in this README (especially the order of location blocks and proxy_pass http://127.0.0.1:8000;).

After any frontend changes, restart npm run dev.

After any Nginx changes, run sudo systemctl restart nginx.

Clear your browser cache or use an Incognito/Private window.

Backend (FastAPI) is Inaccessible (e.g., Cannot connect to host 127.0.0.1:8000 error):

Confirm that uvicorn app.main:app --host 127.0.0.1 --port 8000 is running in a separate terminal without errors.

Check if port 8000 is listening using sudo netstat -tuln | grep 8000.

Test FastAPI connectivity from within the server using curl http://127.0.0.1:8000/api/v1/bot-management/status.

WebSocket for Analysis Logs Not Working:

Ensure Nginx is correctly configured for WebSockets (the proxy_http_version 1.1;, proxy_set_header Upgrade $http_upgrade;, and proxy_set_header Connection "upgrade"; lines in the location /api/ block).

Future Enhancements
Full Authentication (JWT): Implement a more robust authentication system for the API and UI.

Advanced Error Handling: Improve error handling and display more user-friendly messages.

More Trading Strategies: Add new and configurable trading strategies.

Enhanced Dashboard: Incorporate charts and data visualizations for better bot performance analysis.

Notifications: Implement a notification system (e.g., via Telegram or email) for important events.

License
This project is released under the MIT License. See the LICENSE file for more details.
