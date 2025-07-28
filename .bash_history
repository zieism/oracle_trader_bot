cd oracle-trader-frontend
npm run dev -- --host 0.0.0.0
ping google.com
sudo apt update
sudo apt install python3.9 python3.9-venv python3-pip build-essential libpq-dev
sudo apt install postgresql postgresql-contrib
sudo -i -u postgres
sudo apt install curl
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g yarn
sudo apt install nginx
sudo apt install apache2-utils
ls
tar -xvzf oracle_trader_bot.tar.gz
ls
tar -xvzf oracle_trader_frontend.tar.gz
ls
cd /root/oracle_trader_bot
python3.9 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg psycopg2-binary python-dotenv ccxt pandas numpy pydantic-settings aiohttp psutil
nano .env
sudo systemctl status postgresql
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
ls
python bot_engine.py
sudo -u postgres psql
exit
psql -U zieism -d zidb -h localhost
sudo find / -name pg_hba.conf
psql -U zieism -d zidb -h localhost
nano /etc/postgresql/16/main/pg_hba.conf
psql -U zieism -d zidb -h localhost
sudo -u postgres psql
psql -U zieism -d zidb -h localhost
ls
cd oracle_trader_bot
ls
source venv/bin/activate
python bot_engine.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
python bot_engine.py
nano /etc/nginx/sites-available/oracle_bot
sudo netstat -tuln | grep 8000
cd oracle_trader_bot
source venv/bin/activate
sudo netstat -tuln | grep 8000
curl http://127.0.0.1:8000/api/v1/bot-management/status
sudo htpasswd -c /etc/nginx/.htpasswd your_nginx_username
sudo htpasswd -c /etc/nginx/.htpasswd zieism
sudo nano /etc/nginx/sites-available/oracle_bot
sudo ln -s /etc/nginx/sites-available/oracle_bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
nano src/services/apiService.ts
