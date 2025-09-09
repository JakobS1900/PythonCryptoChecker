"""
Email notification service for user engagement and communications.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from logger import logger


class EmailService:
    """Service for sending email notifications."""
    
    def __init__(self):
        self.smtp_enabled = False
        
        # SMTP configuration (would be loaded from environment variables)
        self.smtp_config = {
            "server": "smtp.gmail.com",  # Example SMTP server
            "port": 587,
            "username": "",
            "password": "",
            "from_email": "noreply@cryptogaming.com",
            "from_name": "CryptoGaming Platform"
        }
        
        # Email templates
        self.email_templates = self._initialize_email_templates()
        
        # Rate limiting and mock storage
        self.mock_sent_emails = []
        self.rate_limit_storage = {}
    
    def _initialize_email_templates(self) -> Dict[str, Dict[str, str]]:
        """Initialize email templates."""
        return {
            "welcome": {
                "subject": "Welcome to CryptoGaming Platform!",
                "html_template": """
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center;">
                        <h1 style="color: white; margin: 0;">🎰 Welcome to CryptoGaming!</h1>
                    </div>
                    
                    <div style="padding: 20px;">
                        <h2>Hello {username}!</h2>
                        <p>Welcome to the ultimate virtual crypto gaming experience! We're excited to have you join our community.</p>
                        
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                            <h3>🎁 Your Welcome Bonus:</h3>
                            <ul>
                                <li>1,000 free GEM coins</li>
                                <li>Starter item pack</li>
                                <li>Access to daily quests</li>
                            </ul>
                        </div>
                        
                        <p>Ready to start gaming? Here's what you can do:</p>
                        <ul>
                            <li>🎲 Play crypto-themed roulette games</li>
                            <li>🎒 Collect and trade virtual items</li>
                            <li>👥 Connect with friends</li>
                            <li>🏆 Unlock achievements and level up</li>
                        </ul>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{dashboard_url}" style="background: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">
                                Start Gaming Now!
                            </a>
                        </div>
                        
                        <p>Remember: This is a completely virtual platform - no real money is involved, just pure gaming fun!</p>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666;">
                        <p>CryptoGaming Platform - Virtual Gaming Experience</p>
                        <p>This email was sent to {email}. If you didn't create this account, please ignore this email.</p>
                    </div>
                </body>
                </html>
                """
            },
            
            "comeback_bonus": {
                "subject": "We missed you! Welcome back bonus inside 🎁",
                "html_template": """
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%); padding: 20px; text-align: center;">
                        <h1 style="color: white; margin: 0;">🎉 Welcome Back!</h1>
                    </div>
                    
                    <div style="padding: 20px;">
                        <h2>Hey {username}, we missed you!</h2>
                        <p>It's been {days_absent} days since your last visit, and we've got some exciting updates waiting for you!</p>
                        
                        <div style="background: #fef3c7; border: 2px solid #f59e0b; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                            <h3 style="margin-top: 0;">🎁 Your Welcome Back Bonus:</h3>
                            <div style="font-size: 24px; font-weight: bold; color: #f59e0b;">{bonus_coins} GEM Coins</div>
                            {bonus_extras}
                        </div>
                        
                        <p>While you were away:</p>
                        <ul>
                            <li>New daily quests have been added</li>
                            <li>Fresh items are available in the marketplace</li>
                            <li>Your friends have been asking about you!</li>
                            <li>Special events may be running</li>
                        </ul>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{dashboard_url}" style="background: #f59e0b; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">
                                Claim Your Bonus!
                            </a>
                        </div>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666;">
                        <p>CryptoGaming Platform - We're glad you're back!</p>
                    </div>
                </body>
                </html>
                """
            },
            
            "achievement_milestone": {
                "subject": "🏆 New Achievement Unlocked!",
                "html_template": """
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 20px; text-align: center;">
                        <h1 style="color: white; margin: 0;">🏆 Achievement Unlocked!</h1>
                    </div>
                    
                    <div style="padding: 20px;">
                        <h2>Congratulations {username}!</h2>
                        <p>You've unlocked a major achievement: <strong>{achievement_name}</strong></p>
                        
                        <div style="background: #ecfdf5; border: 2px solid #10b981; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                            <div style="font-size: 48px; margin-bottom: 10px;">🏆</div>
                            <h3 style="margin: 0; color: #059669;">{achievement_name}</h3>
                            <p style="margin: 10px 0; color: #666;">{achievement_description}</p>
                        </div>
                        
                        <p>This achievement puts you in an elite group of players. Keep up the amazing work!</p>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{achievements_url}" style="background: #10b981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">
                                View All Achievements
                            </a>
                        </div>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666;">
                        <p>CryptoGaming Platform - Celebrating Your Success!</p>
                    </div>
                </body>
                </html>
                """
            },
            
            "weekly_summary": {
                "subject": "📊 Your Weekly Gaming Summary",
                "html_template": """
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 20px; text-align: center;">
                        <h1 style="color: white; margin: 0;">📊 Weekly Summary</h1>
                    </div>
                    
                    <div style="padding: 20px;">
                        <h2>Hey {username}!</h2>
                        <p>Here's how your week went on CryptoGaming:</p>
                        
                        <div style="display: flex; flex-wrap: wrap; gap: 10px; margin: 20px 0;">
                            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; flex: 1; min-width: 150px; text-align: center;">
                                <div style="font-size: 24px; font-weight: bold; color: #6366f1;">{games_played}</div>
                                <div style="font-size: 14px; color: #666;">Games Played</div>
                            </div>
                            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; flex: 1; min-width: 150px; text-align: center;">
                                <div style="font-size: 24px; font-weight: bold; color: #10b981;">{coins_earned}</div>
                                <div style="font-size: 14px; color: #666;">Coins Earned</div>
                            </div>
                        </div>
                        
                        {highlights}
                        
                        <p>Ready for another great week? New quests and challenges await!</p>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{dashboard_url}" style="background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">
                                Continue Gaming
                            </a>
                        </div>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666;">
                        <p>CryptoGaming Platform - Weekly Summary</p>
                        <p><a href="{unsubscribe_url}" style="color: #666;">Unsubscribe from weekly summaries</a></p>
                    </div>
                </body>
                </html>
                """
            }
        }
    
    async def send_email(self, user_id: str, title: str, body: str, template_key: str = None, 
                        variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send email notification."""
        try:
            # For development, we'll mock the email sending
            if not self.smtp_enabled:
                return await self._mock_send_email(user_id, title, body, template_key, variables)
            
            # In production, would get user email from database
            user_email = f"user{user_id}@example.com"  # Mock email
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = title
            message["From"] = f"{self.smtp_config['from_name']} <{self.smtp_config['from_email']}>"
            message["To"] = user_email
            
            # Create HTML content
            if template_key and template_key in self.email_templates:
                html_content = self._render_email_template(template_key, variables or {})
            else:
                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>{title}</h2>
                    <p>{body}</p>
                </body>
                </html>
                """
            
            # Add HTML part
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_config["server"], self.smtp_config["port"]) as server:
                server.starttls(context=context)
                server.login(self.smtp_config["username"], self.smtp_config["password"])
                server.sendmail(
                    self.smtp_config["from_email"], 
                    user_email, 
                    message.as_string()
                )
            
            logger.info(f"Email sent to user {user_id}: {title}")
            
            return {
                "success": True,
                "recipient": user_email,
                "subject": title
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_bulk_email(self, recipients: List[Dict[str, str]], template_key: str, 
                            variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send email to multiple recipients."""
        try:
            results = {
                "total_recipients": len(recipients),
                "successful": 0,
                "failed": 0,
                "errors": []
            }
            
            for recipient in recipients:
                try:
                    # Merge recipient-specific variables
                    recipient_vars = {**(variables or {}), **recipient}
                    
                    result = await self.send_email(
                        recipient.get("user_id", ""),
                        self.email_templates[template_key]["subject"],
                        "",  # Body will be from template
                        template_key,
                        recipient_vars
                    )
                    
                    if result.get("success"):
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"User {recipient.get('user_id', 'unknown')}: {result.get('error')}")
                        
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"User {recipient.get('user_id', 'unknown')}: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to send bulk email: {e}")
            return {"error": str(e)}
    
    async def send_welcome_email(self, user_id: str, username: str, email: str, 
                               dashboard_url: str = None) -> Dict[str, Any]:
        """Send welcome email to new user."""
        variables = {
            "username": username,
            "email": email,
            "dashboard_url": dashboard_url or "https://cryptogaming.com/dashboard"
        }
        
        return await self.send_email(
            user_id, 
            self.email_templates["welcome"]["subject"],
            "",
            "welcome",
            variables
        )
    
    async def send_comeback_email(self, user_id: str, username: str, days_absent: int,
                                bonus_coins: int, bonus_extras: str = "") -> Dict[str, Any]:
        """Send comeback bonus email."""
        variables = {
            "username": username,
            "days_absent": days_absent,
            "bonus_coins": bonus_coins,
            "bonus_extras": bonus_extras,
            "dashboard_url": "https://cryptogaming.com/dashboard"
        }
        
        return await self.send_email(
            user_id,
            self.email_templates["comeback_bonus"]["subject"],
            "",
            "comeback_bonus", 
            variables
        )
    
    async def send_weekly_summary(self, user_id: str, username: str, summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send weekly summary email."""
        variables = {
            "username": username,
            "games_played": summary_data.get("games_played", 0),
            "coins_earned": summary_data.get("coins_earned", 0),
            "highlights": summary_data.get("highlights", ""),
            "dashboard_url": "https://cryptogaming.com/dashboard",
            "unsubscribe_url": f"https://cryptogaming.com/unsubscribe?user={user_id}"
        }
        
        return await self.send_email(
            user_id,
            self.email_templates["weekly_summary"]["subject"],
            "",
            "weekly_summary",
            variables
        )
    
    def configure_smtp(self, server: str, port: int, username: str, password: str,
                      from_email: str, from_name: str = "CryptoGaming Platform"):
        """Configure SMTP settings."""
        self.smtp_config.update({
            "server": server,
            "port": port,
            "username": username,
            "password": password,
            "from_email": from_email,
            "from_name": from_name
        })
        self.smtp_enabled = True
        logger.info("SMTP configured and enabled")
    
    async def _mock_send_email(self, user_id: str, title: str, body: str, 
                              template_key: str = None, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Mock email sending for development."""
        try:
            mock_email = {
                "user_id": user_id,
                "recipient": f"user{user_id}@example.com",
                "subject": title,
                "template": template_key,
                "variables": variables or {},
                "sent_at": datetime.utcnow().isoformat()
            }
            
            self.mock_sent_emails.append(mock_email)
            
            # Keep only last 100 emails to prevent memory issues
            if len(self.mock_sent_emails) > 100:
                self.mock_sent_emails = self.mock_sent_emails[-100:]
            
            logger.info(f"[MOCK EMAIL] Sent to user {user_id}: {title}")
            
            return {
                "success": True,
                "recipient": mock_email["recipient"],
                "subject": title,
                "mock": True
            }
            
        except Exception as e:
            logger.error(f"Failed to mock send email: {e}")
            return {"success": False, "error": str(e)}
    
    def _render_email_template(self, template_key: str, variables: Dict[str, Any]) -> str:
        """Render email template with variables."""
        try:
            template_html = self.email_templates[template_key]["html_template"]
            
            # Simple variable substitution
            for key, value in variables.items():
                placeholder = "{" + key + "}"
                template_html = template_html.replace(placeholder, str(value))
            
            return template_html
            
        except Exception as e:
            logger.error(f"Failed to render email template: {e}")
            return f"<html><body><h2>Email Template Error</h2><p>{str(e)}</p></body></html>"
    
    async def get_mock_sent_emails(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get mock sent emails for development/testing."""
        return self.mock_sent_emails[-limit:] if self.mock_sent_emails else []
    
    async def clear_mock_emails(self):
        """Clear mock email storage."""
        self.mock_sent_emails.clear()
        logger.info("Mock email storage cleared")
    
    def get_email_templates(self) -> List[str]:
        """Get available email template keys."""
        return list(self.email_templates.keys())
    
    async def test_email_connection(self) -> Dict[str, Any]:
        """Test SMTP connection."""
        try:
            if not self.smtp_enabled:
                return {"success": False, "error": "SMTP not configured"}
            
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_config["server"], self.smtp_config["port"]) as server:
                server.starttls(context=context)
                server.login(self.smtp_config["username"], self.smtp_config["password"])
            
            return {"success": True, "message": "SMTP connection successful"}
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return {"success": False, "error": str(e)}


# Global instance
email_service = EmailService()