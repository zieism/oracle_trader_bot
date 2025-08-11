# SSH Key Generation Guide for Oracle Trader Bot Server Access

## Recommended SSH Key Configuration
- **Key Type**: ED25519 (most secure and modern)
- **Key Size**: 256-bit (default for ED25519)
- **Format**: OpenSSH
- **Alternative**: RSA 4096-bit if ED25519 not supported

## Generate SSH Key (Linux/macOS/Windows Git Bash)
```bash
# Generate ED25519 key (recommended)
ssh-keygen -t ed25519 -C "oracle-trader-bot-access" -f oracle_trader_key

# Or generate RSA 4096-bit key (alternative)
ssh-keygen -t rsa -b 4096 -C "oracle-trader-bot-access" -f oracle_trader_key
```

## What to share:
1. **Private Key**: The contents of `oracle_trader_key` file (this is what you share with me)
2. **Public Key**: The contents of `oracle_trader_key.pub` file (this goes to server)

## Server Setup (for your reference):
```bash
# On your server (194.127.178.181)
# Add the public key to authorized_keys
echo "PUBLIC_KEY_CONTENT_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

## Security Notes:
- The private key should be treated as highly confidential
- Consider using a passphrase for additional security
- Revoke access by removing the public key from server when done

## Test Connection:
```bash
ssh -i oracle_trader_key root@194.127.178.181
```

## Deployment Tasks I'll Perform:
1. Connect to server via SSH
2. Navigate to project directory
3. Pull latest changes from GitHub
4. Restart Docker containers
5. Monitor deployment logs
6. Test all endpoints
7. Report deployment status

Please generate the key with above specifications and share the private key content with me.
