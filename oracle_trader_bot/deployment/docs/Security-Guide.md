# Oracle Trader Bot - Security Guide

This document outlines security best practices and configurations for deploying the Oracle Trader Bot in production environments.

## Table of Contents

1. [Infrastructure Security](#infrastructure-security)
2. [Application Security](#application-security)
3. [Network Security](#network-security)
4. [Data Protection](#data-protection)
5. [Access Control](#access-control)
6. [Monitoring & Incident Response](#monitoring--incident-response)
7. [Security Checklist](#security-checklist)

## Infrastructure Security

### Server Hardening

#### 1. Operating System Security

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Remove unnecessary packages
sudo apt autoremove -y

# Configure automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades

# Set secure kernel parameters
echo "kernel.yama.ptrace_scope = 1" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.conf.default.rp_filter = 1" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.conf.all.rp_filter = 1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

#### 2. SSH Hardening

```bash
# Create SSH configuration backup
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Edit SSH configuration
sudo nano /etc/ssh/sshd_config
```

Recommended SSH configuration:
```
# Change default port
Port 2222

# Disable root login
PermitRootLogin no

# Use key-based authentication only
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys

# Limit login attempts
MaxAuthTries 3
MaxSessions 2

# Set session timeouts
ClientAliveInterval 300
ClientAliveCountMax 2

# Restrict users
AllowUsers oracle-trader

# Protocol version
Protocol 2

# Disable dangerous features
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
PermitTunnel no
```

#### 3. User Account Security

```bash
# Create dedicated service account
sudo adduser --system --group --home /opt/oracle-trader oracle-trader
sudo usermod -aG docker oracle-trader

# Set secure password policy
sudo apt install libpam-pwquality
echo "minlen=12" | sudo tee -a /etc/security/pwquality.conf
echo "dcredit=-1" | sudo tee -a /etc/security/pwquality.conf
echo "ucredit=-1" | sudo tee -a /etc/security/pwquality.conf
echo "ocredit=-1" | sudo tee -a /etc/security/pwquality.conf
echo "lcredit=-1" | sudo tee -a /etc/security/pwquality.conf

# Configure sudo access
echo "oracle-trader ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose, /bin/systemctl" | sudo tee /etc/sudoers.d/oracle-trader
```

### Firewall Configuration

#### 1. UFW (Uncomplicated Firewall)

```bash
# Reset firewall rules
sudo ufw --force reset

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow essential services
sudo ufw allow 2222/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Rate limiting for SSH
sudo ufw limit 2222/tcp

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status verbose
```

#### 2. Advanced iptables Rules

```bash
# Create iptables rules file
sudo nano /etc/iptables/rules.v4
```

Example iptables configuration:
```bash
#!/bin/bash
# Flush existing rules
iptables -F
iptables -t nat -F
iptables -t mangle -F

# Set default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Rate limit SSH
iptables -A INPUT -p tcp --dport 2222 -m limit --limit 3/min --limit-burst 3 -j ACCEPT

# Allow HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Drop invalid packets
iptables -A INPUT -m state --state INVALID -j DROP

# Log dropped packets
iptables -A INPUT -j LOG --log-prefix "DROPPED: "
```

### Intrusion Detection

#### 1. Fail2Ban Configuration

```bash
# Install fail2ban
sudo apt install fail2ban

# Create local configuration
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Edit configuration
sudo nano /etc/fail2ban/jail.local
```

Fail2Ban configuration:
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
backend = systemd

[sshd]
enabled = true
port = 2222
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
```

#### 2. File Integrity Monitoring

```bash
# Install AIDE
sudo apt install aide

# Initialize database
sudo aideinit

# Create check script
cat << 'EOF' > /opt/oracle-trader/check-integrity.sh
#!/bin/bash
aide --check
if [ $? -ne 0 ]; then
    echo "File integrity check failed!" | mail -s "AIDE Alert" admin@yourdomain.com
fi
EOF

# Add to crontab
echo "0 3 * * * /opt/oracle-trader/check-integrity.sh" | sudo crontab -
```

## Application Security

### Docker Security

#### 1. Container Security

```bash
# Use non-root user in containers
# (Already configured in Dockerfile)

# Set resource limits
# (Configured in docker-compose.prod.yml)

# Use security options
```

Docker Compose security configuration:
```yaml
services:
  oracle-trader:
    security_opt:
      - no-new-privileges:true
      - seccomp:unconfined
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
```

#### 2. Image Security

```bash
# Scan images for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  -v $PWD/cache:/tmp/cache \
  aquasec/trivy image oracle-trader-app

# Use official base images only
# Keep images updated
# Remove unnecessary packages
```

### Environment Variables Security

#### 1. Secure Secret Management

```bash
# Use strong passwords
openssl rand -base64 32

# Encrypt sensitive environment file
gpg --symmetric --cipher-algo AES256 .env

# Use Docker secrets for sensitive data
echo "your-secret" | docker secret create db_password -
```

#### 2. Environment File Protection

```bash
# Set secure permissions
chmod 600 .env
chown oracle-trader:oracle-trader .env

# Backup encrypted
gpg --symmetric --cipher-algo AES256 .env
mv .env.gpg backups/
```

### API Security

#### 1. Rate Limiting

Nginx rate limiting configuration:
```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

# Apply to locations
location /api/ {
    limit_req zone=api burst=20 nodelay;
}

location /auth/ {
    limit_req zone=login burst=3 nodelay;
}
```

#### 2. Authentication & Authorization

```python
# Use strong JWT secrets
JWT_SECRET_KEY = secrets.token_urlsafe(32)

# Implement proper token expiration
JWT_EXPIRATION_HOURS = 1

# Use HTTPS only
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
```

## Network Security

### SSL/TLS Configuration

#### 1. Strong Cipher Suites

Nginx SSL configuration:
```nginx
# Modern SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;

# HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# Security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

#### 2. Certificate Management

```bash
# Use strong DH parameters
openssl dhparam -out dhparam.pem 2048

# Auto-renewal setup
echo "0 2 * * * certbot renew --quiet" | sudo crontab -

# Monitor certificate expiration
./scripts/monitor.sh --check-ssl
```

### Network Segmentation

#### 1. Docker Networks

```yaml
# Isolate services with custom networks
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

services:
  nginx:
    networks:
      - frontend
  
  oracle-trader:
    networks:
      - frontend
      - backend
  
  postgres:
    networks:
      - backend
```

#### 2. VPN Access (Optional)

```bash
# Install WireGuard for secure admin access
sudo apt install wireguard

# Generate keys
wg genkey | tee privatekey | wg pubkey > publickey

# Configure VPN server
sudo nano /etc/wireguard/wg0.conf
```

## Data Protection

### Database Security

#### 1. PostgreSQL Hardening

```sql
-- Enable SSL
ALTER SYSTEM SET ssl = on;

-- Set strong authentication
ALTER SYSTEM SET password_encryption = 'scram-sha-256';

-- Audit logging
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;

-- Connection limits
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET superuser_reserved_connections = 3;
```

#### 2. Backup Encryption

```bash
# Encrypt backups
./scripts/backup.sh --encrypt

# Use remote encrypted storage
./scripts/backup.sh --encrypt --remote
```

### Redis Security

```bash
# Configure Redis security
docker-compose exec redis redis-cli CONFIG SET requirepass "strong-password"
docker-compose exec redis redis-cli CONFIG SET rename-command FLUSHDB ""
docker-compose exec redis redis-cli CONFIG SET rename-command FLUSHALL ""
```

## Access Control

### Administrative Access

#### 1. SSH Key Management

```bash
# Generate ED25519 key pair (client side)
ssh-keygen -t ed25519 -C "admin@yourdomain.com"

# Copy public key to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub -p 2222 oracle-trader@your-server

# Disable password authentication
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

#### 2. Sudo Configuration

```bash
# Limit sudo access
echo "oracle-trader ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose" | sudo tee /etc/sudoers.d/oracle-trader

# Log sudo usage
echo "Defaults logfile=/var/log/sudo.log" | sudo tee -a /etc/sudoers
```

### Application Access

#### 1. Admin Interface Restrictions

```nginx
# Restrict admin access by IP
location /admin/ {
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    allow 192.168.0.0/16;
    # allow YOUR_ADMIN_IP;
    deny all;
    
    proxy_pass http://oracle_trader_backend;
}
```

#### 2. Multi-Factor Authentication

```python
# Implement TOTP for admin accounts
from pyotp import TOTP

def verify_totp(secret, token):
    totp = TOTP(secret)
    return totp.verify(token, valid_window=1)
```

## Monitoring & Incident Response

### Security Monitoring

#### 1. Log Aggregation

```bash
# Install rsyslog
sudo apt install rsyslog

# Configure centralized logging
echo "*.* @@your-log-server:514" | sudo tee -a /etc/rsyslog.conf
sudo systemctl restart rsyslog
```

#### 2. Security Alerts

```bash
# Monitor authentication failures
tail -f /var/log/auth.log | grep "Failed password"

# Monitor file changes
inotifywait -m -r -e modify,create,delete /opt/oracle-trader/

# Custom alert script
./scripts/monitor.sh --security-check
```

### Incident Response

#### 1. Incident Response Plan

1. **Detection**: Automated alerts and monitoring
2. **Containment**: Isolate affected systems
3. **Eradication**: Remove threat and vulnerabilities
4. **Recovery**: Restore services safely
5. **Lessons Learned**: Document and improve

#### 2. Emergency Procedures

```bash
# Emergency shutdown
docker-compose down

# Block suspicious IP
sudo ufw insert 1 deny from SUSPICIOUS_IP

# Change passwords immediately
./scripts/rotate-secrets.sh

# Create incident report
./scripts/incident-report.sh
```

## Security Checklist

### Pre-Deployment

- [ ] Server hardening completed
- [ ] SSH properly configured
- [ ] Firewall rules configured
- [ ] Strong passwords generated
- [ ] SSL certificates configured
- [ ] Security monitoring enabled

### Post-Deployment

- [ ] All services running securely
- [ ] Monitoring alerts configured
- [ ] Backup encryption tested
- [ ] Access controls verified
- [ ] Incident response plan ready
- [ ] Security documentation updated

### Regular Maintenance

- [ ] Security updates applied
- [ ] Passwords rotated
- [ ] Certificates renewed
- [ ] Logs reviewed
- [ ] Backup integrity verified
- [ ] Security scan performed

### Monthly Security Review

- [ ] Review access logs
- [ ] Update security policies
- [ ] Test incident response
- [ ] Review and update firewall rules
- [ ] Vulnerability assessment
- [ ] Security awareness training

## Security Tools & Resources

### Recommended Tools

1. **Vulnerability Scanning**: Nessus, OpenVAS
2. **Network Monitoring**: Nagios, Zabbix
3. **Log Analysis**: ELK Stack, Splunk
4. **Security Scanning**: Nmap, Nikto
5. **Intrusion Detection**: Suricata, Snort

### Security Resources

- [OWASP Security Guidelines](https://owasp.org/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)

## Compliance Considerations

### Data Protection Regulations

- **GDPR**: If handling EU user data
- **CCPA**: If handling California resident data
- **Financial Regulations**: Depending on trading activities

### Audit Requirements

- Maintain detailed logs
- Document all security measures
- Regular security assessments
- Incident response documentation

Remember: Security is an ongoing process, not a one-time setup. Regular reviews and updates are essential for maintaining a secure environment.