"""
Telegram Bot Service for ConnectifyVPN Premium Suite

This module handles all Telegram bot interactions with premium UI/UX,
inline keyboards, and smooth user flows.
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from uuid import uuid4

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
    LabeledPrice, PreCheckoutQuery, BufferedInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import I18n
import qrcode
from io import BytesIO

from core.config import Settings
from core.database import DatabaseManager
from core.models import (
    User, Plan, Account, Order, Ticket, Server, 
    PlanType, PaymentStatus, AccountStatus, VPNProtocol
)
from services.vpn import VPNProvisioningService
from services.payment import PaymentService
from utils.ui import UIGenerator
from utils.helpers import validate_email, validate_phone
from utils.helpers import format_currency, format_date, generate_qr_code


class TelegramBotService:
    """
    Premium Telegram Bot Service with advanced features
    """
    
    def __init__(self, settings: Settings, db: DatabaseManager):
        self.settings = settings
        self.db = db
        self.logger = settings.logger.getChild("telegram_bot")
        
        # Initialize bot
        self.bot = Bot(
            token=settings.telegram.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        self.dp = Dispatcher()
        self.router = Router()
        
        # Services
        self.vpn_service = None
        self.payment_service = None
        
        # UI Generator
        self.ui = UIGenerator(settings)
        
        # User session storage (Redis-backed)
        self.user_sessions = {}
        
        # Register handlers
        self._register_handlers()
        
    def _register_handlers(self):
        """Register all bot handlers"""
        # Command handlers
        self.router.message.register(self.cmd_start, CommandStart())
        self.router.message.register(self.cmd_help, Command("help"))
        self.router.message.register(self.cmd_account, Command("account"))
        self.router.message.register(self.cmd_admin, Command("admin"))
        
        # Callback handlers
        self.router.callback_query.register(self.cbk_home, F.data == "home")
        self.router.callback_query.register(self.cbk_buy, F.data == "buy")
        self.router.callback_query.register(self.cbk_account, F.data == "account")
        self.router.callback_query.register(self.cbk_renew, F.data == "renew")
        self.router.callback_query.register(self.cbk_support, F.data == "support")
        
        # Plan selection
        self.router.callback_query.register(self.cbk_plan, F.data.startswith("plan:"))
        self.router.callback_query.register(self.cbk_pay, F.data.startswith("pay:"))
        self.router.callback_query.register(self.cbk_check_payment, F.data.startswith("check:"))
        self.router.callback_query.register(self.cbk_cancel, F.data.startswith("cancel:"))
        self.router.callback_query.register(self.cbk_rules, F.data.startswith("rules:"))
        self.router.callback_query.register(self.cbk_agree, F.data.startswith("agree:"))
        
        # Account management
        self.router.callback_query.register(self.cbk_copy_config, F.data == "copycfg")
        self.router.callback_query.register(self.cbk_qr_config, F.data == "qrcfg")
        self.router.callback_query.register(self.cbk_speed_test, F.data == "speedtest")
        self.router.callback_query.register(self.cbk_switch_server, F.data == "switchsrv")
        
        # Support
        self.router.callback_query.register(self.cbk_open_ticket, F.data == "ticket:open")
        self.router.callback_query.register(self.cbk_view_tickets, F.data == "ticket:view")
        
        # Admin handlers
        self.router.message.register(self.admin_broadcast, Command("broadcast"))
        self.router.message.register(self.admin_servers, Command("servers"))
        self.router.message.register(self.admin_users, Command("users"))
        self.router.message.register(self.admin_stats, Command("stats"))
        
        # Include router
        self.dp.include_router(self.router)
        
    async def start(self):
        """Start the bot service"""
        self.logger.info("🤖 Starting Telegram Bot Service...")
        
        if self.settings.telegram.webhook_url:
            # Webhook mode (production)
            webhook_url = f"{self.settings.telegram.webhook_url}/webhook"
            await self.bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "callback_query", "inline_query"]
            )
            self.logger.info(f"🌐 Webhook set to: {webhook_url}")
        else:
            # Polling mode (development)
            await self.dp.start_polling(
                self.bot,
                handle_signals=False,
                timeout=self.settings.telegram.polling_timeout
            )
            
    async def stop(self):
        """Stop the bot service"""
        self.logger.info("🛑 Stopping Telegram Bot Service...")
        await self.bot.session.close()
        
    # Command Handlers
    async def cmd_start(self, message: Message):
        """Handle /start command with premium welcome"""
        user = await self.get_or_create_user(message.from_user)
        
        # Get user's active account
        account = await self.get_user_active_account(user.id)
        
        if account:
            # Show account dashboard
            await self.show_account_dashboard(message, user, account)
        else:
            # Show welcome message with premium UI
            await self.show_welcome_message(message, user)
            
    async def cmd_help(self, message: Message):
        """Handle /help command"""
        help_text = self.ui.generate_help_message()
        keyboard = self.ui.get_help_keyboard()
        
        await message.answer(
            help_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
    async def cmd_account(self, message: Message):
        """Handle /account command"""
        user = await self.get_or_create_user(message.from_user)
        account = await self.get_user_active_account(user.id)
        
        if account:
            await self.show_account_dashboard(message, user, account)
        else:
            await self.show_no_account_message(message)
            
    async def cmd_admin(self, message: Message):
        """Handle /admin command"""
        if not await self.is_admin(message.from_user.id):
            await message.answer("❌ You don't have admin privileges.")
            return
            
        await self.show_admin_dashboard(message)
        
    # Callback Handlers
    async def cbk_home(self, callback_query: CallbackQuery):
        """Handle home callback"""
        user = await self.get_or_create_user(callback_query.from_user)
        account = await self.get_user_active_account(user.id)
        
        if account:
            await self.show_account_dashboard(callback_query.message, user, account)
        else:
            await self.show_welcome_message(callback_query.message, user)
            
        await callback_query.answer()
        
    async def cbk_buy(self, callback_query: CallbackQuery):
        """Handle buy callback - show premium plan selection"""
        plans = await self.get_available_plans()
        
        message = self.ui.generate_plan_selection_message(plans)
        keyboard = self.ui.generate_plan_keyboard(plans)
        
        await callback_query.message.edit_text(
            message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await callback_query.answer()
        
    async def cbk_plan(self, callback_query: CallbackQuery):
        """Handle plan selection"""
        plan_code = callback_query.data.split(":", 1)[1]
        user = await self.get_or_create_user(callback_query.from_user)
        
        # Check if trial already used
        if plan_code == "trial" and await self.has_used_trial(user.id):
            await self.show_trial_used_message(callback_query)
            return
            
        plan = await self.get_plan_by_code(plan_code)
        if not plan:
            await callback_query.answer("Plan not found!", show_alert=True)
            return
            
        # Show checkout
        checkout_message = self.ui.generate_checkout_message(plan, user)
        checkout_keyboard = self.ui.generate_checkout_keyboard(plan)
        
        await callback_query.message.edit_text(
            checkout_message,
            reply_markup=checkout_keyboard,
            parse_mode=ParseMode.HTML
        )
        await callback_query.answer()
        
    async def cbk_pay(self, callback_query: CallbackQuery):
        """Handle payment initiation"""
        plan_code = callback_query.data.split(":", 1)[1]
        user = await self.get_or_create_user(callback_query.from_user)
        
        # Check trial usage
        if plan_code == "trial" and await self.has_used_trial(user.id):
            await self.show_trial_used_message(callback_query)
            return
            
        # Create order
        order = await self.create_order(user, plan_code)
        
        # Generate payment link
        payment_url = await self.payment_service.create_payment_link(order)
        
        # Show payment pending
        pending_message = self.ui.generate_payment_pending_message(order, payment_url)
        pending_keyboard = self.ui.generate_payment_keyboard(order, payment_url)
        
        await callback_query.message.edit_text(
            pending_message,
            reply_markup=pending_keyboard,
            parse_mode=ParseMode.HTML
        )
        await callback_query.answer()
        
    async def cbk_check_payment(self, callback_query: CallbackQuery):
        """Check payment status"""
        order_id = callback_query.data.split(":", 1)[1]
        order = await self.get_order_by_id(order_id)
        
        if not order:
            await callback_query.answer("Order not found!", show_alert=True)
            return
            
        # Check with payment gateway
        is_paid = await self.payment_service.check_payment_status(order)
        
        if is_paid:
            await self.process_successful_payment(callback_query, order)
        else:
            await callback_query.answer(
                "Payment still pending. Please complete payment and try again.",
                show_alert=True
            )
            
    async def cbk_agree(self, callback_query: CallbackQuery):
        """Handle terms agreement"""
        order_id = callback_query.data.split(":", 1)[1]
        order = await self.get_order_by_id(order_id)
        
        if not order or not order.is_paid:
            await callback_query.answer("Payment not verified!", show_alert=True)
            return
            
        # Mark terms as accepted
        await self.accept_terms(order)
        
        # Create VPN account
        account = await self.create_vpn_account(order)
        
        # Show success with config
        await self.show_account_activated(callback_query, account)
        
    async def cbk_copy_config(self, callback_query: CallbackQuery):
        """Handle copy config request"""
        user = await self.get_or_create_user(callback_query.from_user)
        account = await self.get_user_active_account(user.id)
        
        if not account:
            await callback_query.answer("No active account!", show_alert=True)
            return
            
        config_links = account.config_links
        
        # Format config message
        config_message = self.ui.generate_config_message(account, config_links)
        
        await callback_query.message.answer(
            config_message,
            parse_mode=ParseMode.MARKDOWN
        )
        await callback_query.answer("✅ Config sent!")
        
    async def cbk_qr_config(self, callback_query: CallbackQuery):
        """Handle QR code request"""
        user = await self.get_or_create_user(callback_query.from_user)
        account = await self.get_user_active_account(user.id)
        
        if not account:
            await callback_query.answer("No active account!", show_alert=True)
            return
            
        config_links = account.config_links
        
        # Generate QR for primary link
        primary_link = config_links.get("vless_tls", "")
        if primary_link:
            qr_image = generate_qr_code(primary_link)
            
            await callback_query.message.answer_photo(
                BufferedInputFile(qr_image, filename="config_qr.png"),
                caption="📱 Scan this QR code with your VPN app"
            )
            
        await callback_query.answer("✅ QR code sent!")
        
    async def cbk_open_ticket(self, callback_query: CallbackQuery):
        """Handle open ticket request"""
        # Set user state to expect ticket description
        user = await self.get_or_create_user(callback_query.from_user)
        await self.set_user_state(user.id, "awaiting_ticket_description")
        
        ticket_message = self.ui.generate_ticket_instructions()
        
        await callback_query.message.answer(ticket_message)
        await callback_query.answer()
        
    # Premium Features
    async def show_welcome_message(self, message: Message, user: User):
        """Show premium welcome message with animation"""
        welcome_text = self.ui.generate_welcome_message(user)
        welcome_keyboard = self.ui.get_welcome_keyboard()
        
        # Send with premium styling
        await message.answer(
            welcome_text,
            reply_markup=welcome_keyboard,
            parse_mode=ParseMode.HTML
        )
        
    async def show_account_dashboard(self, message: Message, user: User, account: Account):
        """Show premium account dashboard"""
        dashboard_text = self.ui.generate_dashboard_message(user, account)
        dashboard_keyboard = self.ui.get_dashboard_keyboard(account)
        
        await message.edit_text(
            dashboard_text,
            reply_markup=dashboard_keyboard,
            parse_mode=ParseMode.HTML
        )
        
    async def show_admin_dashboard(self, message: Message):
        """Show admin dashboard with real-time stats"""
        stats = await self.get_admin_stats()
        admin_text = self.ui.generate_admin_dashboard(stats)
        admin_keyboard = self.ui.get_admin_keyboard()
        
        await message.answer(
            admin_text,
            reply_markup=admin_keyboard,
            parse_mode=ParseMode.HTML
        )
        
    # Admin Handlers
    async def admin_broadcast(self, message: Message):
        """Handle admin broadcast"""
        if not await self.is_admin(message.from_user.id):
            return
            
        # Extract broadcast message
        broadcast_text = message.text[len("/broadcast "):].strip()
        
        if not broadcast_text:
            await message.answer("Usage: /broadcast <message>")
            return
            
        # Send broadcast to all users
        sent_count = await self.send_broadcast(broadcast_text)
        
        await message.answer(f"📢 Broadcast sent to {sent_count} users")
        
    async def admin_servers(self, message: Message):
        """Show server status"""
        if not await self.is_admin(message.from_user.id):
            return
            
        servers = await self.get_all_servers()
        servers_text = self.ui.generate_servers_status(servers)
        
        await message.answer(servers_text, parse_mode=ParseMode.HTML)
        
    async def admin_stats(self, message: Message):
        """Show system statistics"""
        if not await self.is_admin(message.from_user.id):
            return
            
        stats = await self.get_admin_stats()
        stats_text = self.ui.generate_stats_message(stats)
        
        await message.answer(stats_text, parse_mode=ParseMode.HTML)
        
    # Utility Methods
    async def get_or_create_user(self, telegram_user) -> User:
        """Get or create user from Telegram user"""
        async with self.db.get_session() as session:
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_user.id)
            )
            user = user.scalar_one_or_none()
            
            if not user:
                user = User(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                )
                session.add(user)
                await session.commit()
                
            return user
            
    async def get_user_active_account(self, user_id: int) -> Optional[Account]:
        """Get user's active account"""
        async with self.db.get_session() as session:
            account = await session.execute(
                select(Account)
                .where(
                    Account.user_id == user_id,
                    Account.status == AccountStatus.ACTIVE,
                    Account.expires_at > datetime.utcnow()
                )
                .order_by(Account.expires_at.desc())
                .limit(1)
            )
            return account.scalar_one_or_none()
            
    async def is_admin(self, telegram_id: int) -> bool:
        """Check if user is admin"""
        return telegram_id in self.settings.telegram.admin_ids
        
    async def set_user_state(self, user_id: int, state: str, data: Optional[Dict] = None):
        """Set user state in Redis"""
        redis = await self.db.get_redis()
        state_data = {"state": state}
        if data:
            state_data.update(data)
            
        await redis.setex(
            f"user_state:{user_id}",
            1800,  # 30 minutes
            json.dumps(state_data)
        )
        
    async def get_user_state(self, user_id: int) -> Optional[Dict]:
        """Get user state from Redis"""
        redis = await self.db.get_redis()
        state_data = await redis.get(f"user_state:{user_id}")
        
        if state_data:
            return json.loads(state_data)
        return None
        
    async def clear_user_state(self, user_id: int):
        """Clear user state"""
        redis = await self.db.get_redis()
        await redis.delete(f"user_state:{user_id}")
        
    # Background Tasks
    async def start_background_tasks(self):
        """Start background tasks"""
        tasks = [
            self.expiry_reminder_task(),
            self.health_check_task(),
            self.cleanup_task()
        ]
        
        await asyncio.gather(*tasks)
        
    async def expiry_reminder_task(self):
        """Send expiry reminders"""
        while True:
            try:
                await self.send_expiry_reminders()
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                self.logger.error(f"Error in expiry reminder task: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
                
    async def health_check_task(self):
        """Monitor server health"""
        while True:
            try:
                await self.check_server_health()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                self.logger.error(f"Error in health check task: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
                
    async def cleanup_task(self):
        """Clean up old data"""
        while True:
            try:
                await self.cleanup_old_data()
                await asyncio.sleep(86400)  # Run daily
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
