# app/monitoring/alerting.py
import logging
import asyncio
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings


logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertChannel(str, Enum):
    LOG = "LOG"
    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"
    FILE = "FILE"


@dataclass
class Alert:
    title: str
    message: str
    severity: AlertSeverity
    timestamp: datetime
    source: str
    data: Optional[Dict] = None


@dataclass
class AlertRule:
    name: str
    condition: Callable
    severity: AlertSeverity
    channels: List[AlertChannel]
    cooldown_minutes: int = 5
    enabled: bool = True


class AlertingManager:
    """
    Manages alerting system for critical events, performance issues, and trading anomalies.
    Supports multiple channels: log, email, webhook, file.
    """
    
    def __init__(self):
        self.logger = logger
        self.alert_history: List[Alert] = []
        self.alert_rules: List[AlertRule] = []
        self.last_alert_times: Dict[str, datetime] = {}
        
        # Email configuration (would be loaded from secure config)
        self.email_config = {
            "smtp_server": "smtp.gmail.com",  # Example
            "smtp_port": 587,
            "username": None,  # Set from environment
            "password": None,  # Set from environment
            "from_email": None,  # Set from environment
            "to_emails": []  # Set from environment
        }
        
        # Initialize default alert rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alerting rules."""
        self.alert_rules = [
            AlertRule(
                name="daily_loss_limit_exceeded",
                condition=lambda data: data.get("daily_loss_pct", 0) <= -5.0,
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.EMAIL],
                cooldown_minutes=60
            ),
            AlertRule(
                name="margin_usage_high",
                condition=lambda data: data.get("margin_usage_pct", 0) > 80,
                severity=AlertSeverity.ERROR,
                channels=[AlertChannel.LOG, AlertChannel.EMAIL],
                cooldown_minutes=30
            ),
            AlertRule(
                name="position_pnl_significant_loss",
                condition=lambda data: data.get("position_loss_pct", 0) <= -10.0,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.LOG],
                cooldown_minutes=15
            ),
            AlertRule(
                name="volatility_spike",
                condition=lambda data: data.get("volatility", 0) > 0.15,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.LOG],
                cooldown_minutes=10
            ),
            AlertRule(
                name="emergency_stop_activated",
                condition=lambda data: data.get("emergency_stop", False),
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.EMAIL],
                cooldown_minutes=0  # No cooldown for emergency stops
            )
        ]
    
    async def send_alert(
        self, 
        title: str,
        message: str,
        severity: AlertSeverity,
        source: str = "system",
        data: Optional[Dict] = None,
        channels: Optional[List[AlertChannel]] = None
    ):
        """
        Send alert through specified channels.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity level
            source: Source system/component
            data: Additional data payload
            channels: Specific channels to use (defaults to all)
        """
        try:
            alert = Alert(
                title=title,
                message=message,
                severity=severity,
                timestamp=datetime.utcnow(),
                source=source,
                data=data or {}
            )
            
            # Check cooldown
            alert_key = f"{source}_{title}"
            if self._is_in_cooldown(alert_key, severity):
                self.logger.debug(f"Alert {alert_key} is in cooldown period")
                return
            
            # Record alert
            self.alert_history.append(alert)
            self.last_alert_times[alert_key] = alert.timestamp
            
            # Limit alert history
            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-500:]
            
            # Send through channels
            target_channels = channels or [AlertChannel.LOG]
            
            for channel in target_channels:
                await self._send_to_channel(alert, channel)
            
            self.logger.info(f"Alert sent: {title} ({severity.value}) via {[c.value for c in target_channels]}")
            
        except Exception as e:
            self.logger.error(f"Error sending alert: {e}")
    
    def _is_in_cooldown(self, alert_key: str, severity: AlertSeverity) -> bool:
        """Check if alert is in cooldown period."""
        if severity == AlertSeverity.CRITICAL:
            return False  # No cooldown for critical alerts
        
        last_time = self.last_alert_times.get(alert_key)
        if not last_time:
            return False
        
        # Default cooldown is 5 minutes
        cooldown_minutes = 5
        if severity == AlertSeverity.ERROR:
            cooldown_minutes = 10
        elif severity == AlertSeverity.WARNING:
            cooldown_minutes = 15
        
        time_diff = (datetime.utcnow() - last_time).total_seconds() / 60
        return time_diff < cooldown_minutes
    
    async def _send_to_channel(self, alert: Alert, channel: AlertChannel):
        """Send alert to specific channel."""
        try:
            if channel == AlertChannel.LOG:
                await self._send_to_log(alert)
            elif channel == AlertChannel.EMAIL:
                await self._send_to_email(alert)
            elif channel == AlertChannel.FILE:
                await self._send_to_file(alert)
            elif channel == AlertChannel.WEBHOOK:
                await self._send_to_webhook(alert)
                
        except Exception as e:
            self.logger.error(f"Error sending alert to {channel.value}: {e}")
    
    async def _send_to_log(self, alert: Alert):
        """Send alert to logging system."""
        log_message = f"ALERT [{alert.severity.value}] {alert.title}: {alert.message}"
        
        if alert.severity == AlertSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif alert.severity == AlertSeverity.ERROR:
            self.logger.error(log_message)
        elif alert.severity == AlertSeverity.WARNING:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    async def _send_to_email(self, alert: Alert):
        """Send alert via email."""
        if not self.email_config.get("username") or not self.email_config.get("to_emails"):
            self.logger.warning("Email configuration not complete, skipping email alert")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config["from_email"] or self.email_config["username"]
            msg['To'] = ", ".join(self.email_config["to_emails"])
            msg['Subject'] = f"Oracle Trader Bot Alert: {alert.title}"
            
            body = f"""
Alert Details:
- Title: {alert.title}
- Severity: {alert.severity.value}
- Source: {alert.source}
- Time: {alert.timestamp.isoformat()}
- Message: {alert.message}

Additional Data:
{alert.data if alert.data else 'None'}

---
Oracle Trader Bot Alerting System
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"])
            server.starttls()
            server.login(self.email_config["username"], self.email_config["password"])
            
            text = msg.as_string()
            server.sendmail(msg['From'], self.email_config["to_emails"], text)
            server.quit()
            
            self.logger.info(f"Email alert sent successfully: {alert.title}")
            
        except Exception as e:
            self.logger.error(f"Error sending email alert: {e}")
    
    async def _send_to_file(self, alert: Alert):
        """Send alert to file."""
        try:
            alert_file = f"{settings.LOG_DIR}/alerts.log"
            
            with open(alert_file, 'a') as f:
                alert_line = f"{alert.timestamp.isoformat()} | {alert.severity.value} | {alert.source} | {alert.title} | {alert.message}\n"
                f.write(alert_line)
                
        except Exception as e:
            self.logger.error(f"Error writing alert to file: {e}")
    
    async def _send_to_webhook(self, alert: Alert):
        """Send alert to webhook endpoint."""
        # Placeholder for webhook implementation
        # Would send POST request to configured webhook URL
        pass
    
    async def check_alert_rules(self, monitoring_data: Dict):
        """Check monitoring data against alert rules."""
        try:
            for rule in self.alert_rules:
                if not rule.enabled:
                    continue
                
                try:
                    if rule.condition(monitoring_data):
                        await self.send_alert(
                            title=rule.name.replace("_", " ").title(),
                            message=f"Alert rule '{rule.name}' triggered",
                            severity=rule.severity,
                            source="monitoring",
                            data=monitoring_data,
                            channels=rule.channels
                        )
                except Exception as e:
                    self.logger.error(f"Error evaluating alert rule {rule.name}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error checking alert rules: {e}")
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent alerts within specified hours."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            recent_alerts = [
                {
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity.value,
                    "source": alert.source,
                    "timestamp": alert.timestamp.isoformat(),
                    "data": alert.data
                }
                for alert in self.alert_history
                if alert.timestamp >= cutoff_time
            ]
            
            return sorted(recent_alerts, key=lambda x: x["timestamp"], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error getting recent alerts: {e}")
            return []
    
    def get_alert_summary(self) -> Dict:
        """Get alert system summary."""
        try:
            # Count alerts by severity (last 24 hours)
            recent_alerts = self.get_recent_alerts(24)
            severity_counts = {severity.value: 0 for severity in AlertSeverity}
            
            for alert in recent_alerts:
                severity_counts[alert["severity"]] += 1
            
            return {
                "total_rules": len(self.alert_rules),
                "enabled_rules": len([r for r in self.alert_rules if r.enabled]),
                "total_alerts_24h": len(recent_alerts),
                "severity_counts_24h": severity_counts,
                "last_alert": recent_alerts[0] if recent_alerts else None,
                "email_configured": bool(self.email_config.get("username"))
            }
            
        except Exception as e:
            self.logger.error(f"Error getting alert summary: {e}")
            return {"status": "error"}


# Global instance
alerting_manager = AlertingManager()