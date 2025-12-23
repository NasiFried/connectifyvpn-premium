"""
UI Generator for ConnectifyVPN Premium Suite

This module generates premium UI components with glassmorphism effects,
beautiful layouts, and professional styling.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.config import Settings
from core.models import Account, Plan, Server, User


class UIGenerator:
    """
    Premium UI Generator with glassmorphism design system
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.brand_name = settings.brand_name or "ConnectifyVPN"
        
        # Color palette
        self.colors = {
            'primary': '#16213e',
            'secondary': '#0f3460', 
            'accent': '#e94560',
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'info': '#3498db',
            'light': '#ffffff',
            'dark': '#1a1a2e',
            'muted': '#7f8c8d'
        }
        
    # Core UI Components
    def generate_box(self, title: str, content: List[str], footer: Optional[str] = None) -> str:
        """Generate a beautiful boxed message"""
        lines = []
        
        # Header
        lines.append("╔════════════════════════════════════════╗")
        lines.append(f"║ {title:^38} ║")
        lines.append("╠════════════════════════════════════════╣")
        
        # Content
        for line in content:
            lines.append(f"║ {line:<38} ║")
            
        # Footer
        if footer:
            lines.append("╠════════════════════════════════════════╣")
            lines.append(f"║ {footer:<38} ║")
            
        lines.append("╚════════════════════════════════════════╝")
        
        return "\n".join(lines)
        
    def generate_card(self, title: str, items: Dict[str, str], icon: str = "🛡️") -> str:
        """Generate a premium card layout"""
        lines = []
        
        # Title with icon
        lines.append(f"{icon} <b>{title}</b>")
        lines.append("")
        
        # Items
        for key, value in items.items():
            lines.append(f"<b>{key}:</b> {value}")
            
        return "\n".join(lines)
        
    def generate_welcome_message(self, user: User) -> str:
        """Generate premium welcome message"""
        return f"""
🌟 <b>Welcome to {self.brand_name} Premium Suite!</b>

Hello <b>{user.full_name}</b>! 👋

Experience the ultimate VPN solution with:
• ⚡ <b>Lightning-fast</b> connections
• 🛡️ <b>Military-grade</b> encryption  
• 🌍 <b>Global</b> server network
• 📱 <b>Multi-device</b> support
• 🎯 <b>Smart</b> server selection

Ready to secure your digital freedom? 🚀
        """.strip()
        
    def generate_dashboard_message(self, user: User, account: Account) -> str:
        """Generate premium account dashboard"""
        days_left = account.days_until_expiry
        status_emoji = "✅" if days_left > 7 else "⚠️" if days_left > 3 else "🔴"
        
        items = {
            "Status": f"{status_emoji} Active",
            "Plan": account.plan.name,
            "Server": account.server.name,
            "Location": account.server.location or "Global",
            "Expires": f"{account.expires_at.strftime('%d %b %Y')} ({days_left} days left)",
            "Data Used": f"{account.data_used_gb:.2f} GB",
            "Devices": f"{account.active_devices}/{account.device_limit}"
        }
        
        return self.generate_card("Your Account", items, icon="👤")
        
    def generate_plan_selection_message(self, plans: List[Plan]) -> str:
        """Generate premium plan selection message"""
        message = f"""
🎯 <b>Choose Your Premium Plan</b>

Select the perfect plan for your needs:

"""
        
        for plan in plans:
            if not plan.is_public:
                continue
                
            icon = "🧪" if plan.is_trial else "🛡️"
            features = "\n".join([
                f"  • {feature}" for feature in plan.features.get("highlights", [])
            ])
            
            message += f"""
{icon} <b>{plan.name}</b> - {plan.display_price}
⏱️ Duration: {plan.duration_days} days
📱 Devices: {plan.device_limit}
{features}

"""
        
        message += "💳 Secure payment with multiple options"
        
        return message.strip()
        
    def generate_checkout_message(self, plan: Plan, user: User) -> str:
        """Generate premium checkout message"""
        items = {
            "Plan": plan.name,
            "Duration": f"{plan.duration_days} days",
            "Devices": str(plan.device_limit),
            "Price": plan.display_price,
            "User": user.full_name
        }
        
        return self.generate_card("Checkout", items, icon="🛒")
        
    def generate_payment_pending_message(self, order: Order, payment_url: str) -> str:
        """Generate payment pending message"""
        return f"""
⏳ <b>Payment Pending</b>

Order: <code>{order.order_id}</code>
Amount: <b>{order.amount:.2f} {order.currency}</b>
Status: <i>Waiting for payment</i>

🔄 After payment, click "Check Payment" to activate your account.

💡 <i>Payment is processed securely through our payment gateway.</i>
        """.strip()
        
    def generate_config_message(self, account: Account, links: Dict[str, str]) -> str:
        """Generate VPN config message"""
        message = f"""
⚙️ <b>Your VPN Configuration</b>

Server: <code>{account.server.hostname}</code>
Username: <code>{account.username}</code>
UUID: <code>{str(account.uuid)}</code>

🔗 <b>Connection Links:</b>

"""
        
        for protocol, link in links.items():
            protocol_name = protocol.replace("_", " ").upper()
            message += f"<b>{protocol_name}:</b>\n<code>{link}</code>\n\n"
            
        message += """
📱 <b>Setup Instructions:</b>
1. Download a VPN client (v2rayNG, Shadowrocket, etc.)
2. Import the configuration link
3. Connect and enjoy secure browsing!

💡 <i>Need help? Contact our support team!</i>
        """
        
        return message.strip()
        
    def generate_rules_message(self) -> str:
        """Generate terms and rules message"""
        return f"""
📜 <b>{self.brand_name} Terms of Service</b>

By using our service, you agree to:

✅ <b>Acceptable Use:</b>
• No illegal activities
• No spam or abuse
• No copyright infringement

⚡ <b>Service Terms:</b>
• Fair usage policy applies
• No unauthorized sharing
• Account security is your responsibility

🔒 <b>Privacy:</b>
• We don't log your activities
• Your data is encrypted
• No selling of personal information

⚖️ <b>Violations may result in:</b>
• Immediate account suspension
• No refund for violations
• Legal action if required

🤝 <b>Let's keep the internet safe and free!**
        """.strip()
        
    def generate_help_message(self) -> str:
        """Generate comprehensive help message"""
        return f"""
❓ <b>{self.brand_name} Help Center</b>

🚀 <b>Getting Started:</b>
• /start - Main menu and account overview
• /account - View your account details
• /help - Show this help message

💳 <b>Purchasing:</b>
• Tap "⚡ Buy VPN" to view plans
• Choose your preferred plan
• Complete secure payment
• Get instant access

⚙️ <b>Configuration:</b>
• "📋 Copy Config" - Get VPN links
• "📷 QR Code" - Scan with mobile app
• "🧠 Setup Guide" - Step-by-step instructions

🔄 <b>Account Management:</b>
• "🔄 Renew" - Extend subscription
• "👤 My Account" - View details
• "🎫 Support" - Get help

🛡️ <b>Security:</b>
• Military-grade encryption
• No-log policy
• Multiple protocols supported

📞 <b>Need More Help?</b>
Tap "🛟 Support" to contact our team
        """.strip()
        
    def generate_admin_dashboard(self, stats: Dict[str, Any]) -> str:
        """Generate admin dashboard"""
        items = {
            "Total Users": str(stats.get("total_users", 0)),
            "Active Accounts": str(stats.get("active_accounts", 0)),
            "Total Revenue": f"RM {stats.get('total_revenue', 0):.2f}",
            "Servers Online": str(stats.get("servers_online", 0)),
            "Pending Tickets": str(stats.get("pending_tickets", 0)),
            "System Load": f"{stats.get('system_load', 0):.1f}%"
        }
        
        return self.generate_card("Admin Dashboard", items, icon="⚙️")
        
    def generate_servers_status(self, servers: List[Server]) -> str:
        """Generate servers status message"""
        message = "📊 <b>Server Status Overview</b>\n\n"
        
        for server in servers:
            status_emoji = "🟢" if server.status.value == "online" else "🔴"
            load_bar = self._generate_load_bar(server.utilization_percent)
            
            message += f"""
{status_emoji} <b>{server.name}</b>
   Host: <code>{server.hostname}</code>
   Load: {load_bar} {server.utilization_percent:.1f}%
   Users: {server.active_connections}/{server.capacity}
   Location: {server.location or 'Unknown'}

"""
        
        return message.strip()
        
    def generate_stats_message(self, stats: Dict[str, Any]) -> str:
        """Generate detailed statistics message"""
        items = {
            "Today Revenue": f"RM {stats.get('today_revenue', 0):.2f}",
            "New Users": str(stats.get('new_users_today', 0)),
            "Active Sessions": str(stats.get('active_sessions', 0)),
            "Data Transfer": f"{stats.get('data_transfer_gb', 0):.2f} GB",
            "Avg Response Time": f"{stats.get('avg_response_ms', 0)} ms",
            "Uptime": f"{stats.get('uptime_percent', 100):.2f}%"
        }
        
        return self.generate_card("System Statistics", items, icon="📊")
        
    def generate_ticket_instructions(self) -> str:
        """Generate ticket creation instructions"""
        return f"""
🎫 <b>Create Support Ticket</b>

Please describe your issue in detail:

📋 <b>Include:</b>
• What problem are you experiencing?
• When did it start?
• What device/app are you using?
• Any error messages?

🖼️ <b>Attachments:</b>
• Screenshots are helpful
• Log files if available

⏱️ <b>Response Time:</b>
• Usually within 1-2 hours
• Urgent issues prioritized

Type your message now...
        """.strip()
        
    # Keyboard Generators
    def get_welcome_keyboard(self) -> InlineKeyboardMarkup:
        """Generate welcome keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text="⚡ Buy VPN", callback_data="buy")
        builder.button(text="👤 My Account", callback_data="account")
        builder.button(text="🔄 Renew", callback_data="renew")
        builder.button(text="🧠 Setup Guide", callback_data="guide")
        builder.button(text="🛟 Support", callback_data="support")
        
        builder.adjust(2, 2, 1)
        return builder.as_markup()
        
    def get_dashboard_keyboard(self, account: Account) -> InlineKeyboardMarkup:
        """Generate account dashboard keyboard"""
        builder = InlineKeyboardBuilder()
        
        # Primary actions
        builder.button(text="📋 Copy Config", callback_data="copycfg")
        builder.button(text="📷 QR Code", callback_data="qrcfg")
        
        # Secondary actions
        builder.button(text="🔄 Renew", callback_data="renew")
        builder.button(text="⚡ Speed Test", callback_data="speedtest")
        builder.button(text="🔄 Switch Server", callback_data="switchsrv")
        
        # Support
        builder.button(text="🛟 Support", callback_data="support")
        builder.button(text="🏠 Home", callback_data="home")
        
        builder.adjust(2, 2, 2, 2)
        return builder.as_markup()
        
    def get_plan_keyboard(self, plans: List[Plan]) -> InlineKeyboardMarkup:
        """Generate plan selection keyboard"""
        builder = InlineKeyboardBuilder()
        
        for plan in plans:
            if not plan.is_public:
                continue
                
            icon = "🧪" if plan.is_trial else "🛡️"
            builder.button(
                text=f"{icon} {plan.name} - {plan.display_price}",
                callback_data=f"plan:{plan.type.value}"
            )
            
        builder.button(text="🏠 Home", callback_data="home")
        builder.adjust(1, 1, 1)
        return builder.as_markup()
        
    def get_checkout_keyboard(self, plan: Plan) -> InlineKeyboardMarkup:
        """Generate checkout keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.button(
            text=f"💳 Pay {plan.display_price}",
            callback_data=f"pay:{plan.type.value}"
        )
        builder.button(text="⬅️ Back", callback_data="buy")
        builder.button(text="🏠 Home", callback_data="home")
        
        builder.adjust(1, 2)
        return builder.as_markup()
        
    def get_payment_keyboard(self, order: Order, payment_url: str) -> InlineKeyboardMarkup:
        """Generate payment keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text="✅ Pay Now", url=payment_url)
        builder.button(text="♻️ Check Payment", callback_data=f"check:{order.order_id}")
        builder.button(text="❌ Cancel", callback_data=f"cancel:{order.order_id}")
        
        builder.adjust(1, 2)
        return builder.as_markup()
        
    def get_rules_keyboard(self, order_id: str) -> InlineKeyboardMarkup:
        """Generate terms acceptance keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.button(
            text="✅ I Understand & Agree",
            callback_data=f"agree:{order_id}"
        )
        builder.button(text="🏠 Home", callback_data="home")
        
        builder.adjust(1, 1)
        return builder.as_markup()
        
    def get_help_keyboard(self) -> InlineKeyboardMarkup:
        """Generate help keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text="📚 Setup Guide", callback_data="guide")
        builder.button(text="🎫 Open Ticket", callback_data="ticket:open")
        builder.button(text="💬 Live Chat", callback_data="livechat")
        builder.button(text="🏠 Home", callback_data="home")
        
        builder.adjust(2, 2)
        return builder.as_markup()
        
    def get_admin_keyboard(self) -> InlineKeyboardMarkup:
        """Generate admin keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text="📊 Statistics", callback_data="admin:stats")
        builder.button(text="👥 Users", callback_data="admin:users")
        builder.button(text="🖥️ Servers", callback_data="admin:servers")
        builder.button(text="📢 Broadcast", callback_data="admin:broadcast")
        builder.button(text="⚙️ Settings", callback_data="admin:settings")
        builder.button(text="🔍 Logs", callback_data="admin:logs")
        
        builder.adjust(2, 2, 2)
        return builder.as_markup()
        
    def get_renew_keyboard(self) -> InlineKeyboardMarkup:
        """Generate renewal keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.button(
            text=f"💳 Renew 365 Days (RM{self.settings.payment.full_price})",
            callback_data="pay:renew"
        )
        builder.button(text="🏠 Home", callback_data="home")
        
        builder.adjust(1, 1)
        return builder.as_markup()
        
    # Utility Methods
    def _generate_load_bar(self, percentage: float, length: int = 10) -> str:
        """Generate ASCII load bar"""
        filled = int(length * percentage / 100)
        bar = "█" * filled + "░" * (length - filled)
        return bar
        
    def _format_number(self, num: int) -> str:
        """Format large numbers"""
        if num >= 1000000:
            return f"{num / 1000000:.1f}M"
        elif num >= 1000:
            return f"{num / 1000:.1f}K"
        return str(num)
        
    def _generate_stars(self, rating: float, max_stars: int = 5) -> str:
        """Generate star rating"""
        full_stars = int(rating)
        half_star = 1 if rating % 1 >= 0.5 else 0
        empty_stars = max_stars - full_stars - half_star
        
        return "⭐" * full_stars + "✨" * half_star + "☆" * empty_stars


# Premium UI Themes
class GlassmorphismTheme:
    """Glassmorphism theme for premium UI"""
    
    @staticmethod
    def generate_card(title: str, content: str, accent_color: str = "#e94560") -> str:
        """Generate glassmorphism card"""
        return f"""
<div style="
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 20px;
    margin: 10px 0;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
">
    <h3 style="color: {accent_color}; margin: 0 0 15px 0; font-size: 18px;">
        {title}
    </h3>
    <div style="color: #ffffff; line-height: 1.6;">
        {content}
    </div>
</div>
        """.strip()
        
    @staticmethod
    def generate_button(text: str, url: str, style: str = "primary") -> str:
        """Generate glassmorphism button"""
        styles = {
            "primary": "background: linear-gradient(45deg, #e94560, #ff6b7a);",
            "secondary": "background: linear-gradient(45deg, #16213e, #0f3460);",
            "success": "background: linear-gradient(45deg, #27ae60, #2ecc71);",
        }
        
        return f"""
<a href="{url}" style="
    {styles.get(style, styles['primary'])}
    color: white;
    padding: 12px 24px;
    border: none;
    border-radius: 25px;
    text-decoration: none;
    display: inline-block;
    margin: 5px;
    font-weight: bold;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    backdrop-filter: blur(5px);
    transition: all 0.3s ease;
">{text}</a>
        """.strip()


class NeonTheme:
    """Neon theme for futuristic UI"""
    
    @staticmethod
    def generate_glow_card(title: str, content: str, glow_color: str = "#00ffff") -> str:
        """Generate neon glow card"""
        return f"""
<div style="
    background: rgba(0, 0, 0, 0.8);
    border: 2px solid {glow_color};
    border-radius: 15px;
    padding: 20px;
    margin: 10px 0;
    box-shadow: 0 0 30px {glow_color}40, inset 0 0 20px {glow_color}20;
">
    <h3 style="color: {glow_color}; text-shadow: 0 0 10px {glow_color}; margin: 0 0 15px 0;">
        {title}
    </h3>
    <div style="color: #ffffff; text-shadow: 0 0 5px rgba(255, 255, 255, 0.5);">
        {content}
    </div>
</div>
        """.strip()
        
    @staticmethod
    def generate_neon_button(text: str, callback_data: str, color: str = "#00ffff") -> str:
        """Generate neon button"""
        return f"""
<button style="
    background: transparent;
    color: {color};
    border: 2px solid {color};
    border-radius: 25px;
    padding: 10px 20px;
    font-weight: bold;
    text-shadow: 0 0 5px {color};
    box-shadow: 0 0 10px {color}40, inset 0 0 5px {color}20;
    transition: all 0.3s ease;
    cursor: pointer;
" onmouseover="this.style.boxShadow='0 0 20px {color}80, inset 0 0 10px {color}40'" onmouseout="this.style.boxShadow='0 0 10px {color}40, inset 0 0 5px {color}20'">
    {text}
</button>
        """.strip()
