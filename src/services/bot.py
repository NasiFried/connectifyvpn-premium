"""
Telegram Bot Service for ConnectifyVPN Premium Suite

Premium UI/UX, inline keyboards, smooth user flows.
This version is FIXED to avoid missing cbk_* handlers,
and is COMPATIBLE with your current DatabaseManager (db.session()).
It also works when REDIS is disabled (fallback to in-memory state).
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import uuid4

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sqlalchemy import select, text

from core.config import Settings
from core.database import DatabaseManager
from core.models import (
    User, Plan, Account, Order, Ticket, Server,
    PlanType, PaymentStatus, AccountStatus, VPNProtocol
)

from services.vpn import VPNProvisioningService
from services.payment import PaymentService
from utils.ui import UIGenerator
from utils.helpers import generate_qr_code


class TelegramBotService:
    """
    Premium Telegram Bot Service with advanced features
    """

    def __init__(self, settings: Settings, db: DatabaseManager):
        self.settings = settings
        self.db = db

        # logger + brand_name MUST exist in Settings (kau dah add sebelum ni)
        self.logger = getattr(settings, "logger", None)
        if self.logger:
            self.logger = self.logger.getChild("telegram_bot")

        # Initialize bot
        self.bot = Bot(
            token=settings.telegram.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        self.dp = Dispatcher()
        self.router = Router()

        # Services (real implementations in your project)
        self.vpn_service = VPNProvisioningService(settings, db)
        self.payment_service = PaymentService(settings, db)

        # UI Generator
        self.ui = UIGenerator(settings)

        # User state storage:
        # - if Redis enabled & available: use redis_client
        # - else fallback: in-memory dict
        self._state_mem: Dict[int, Dict[str, Any]] = {}

        # Register handlers
        self._register_handlers()

    # ==========================================================
    # HANDLER REGISTRATION
    # ==========================================================
    def _register_handlers(self):
        """Register all bot handlers"""

        # Command handlers
        self.router.message.register(self.cmd_start, CommandStart())
        self.router.message.register(self.cmd_help, Command("help"))
        self.router.message.register(self.cmd_account, Command("account"))
        self.router.message.register(self.cmd_admin, Command("admin"))

        # Admin handlers (command)
        self.router.message.register(self.admin_broadcast, Command("broadcast"))
        self.router.message.register(self.admin_servers, Command("servers"))
        self.router.message.register(self.admin_users, Command("users"))
        self.router.message.register(self.admin_stats, Command("stats"))

        # Callback handlers (MAIN NAV)
        self.router.callback_query.register(self.cbk_home, F.data == "home")
        self.router.callback_query.register(self.cbk_buy, F.data == "buy")
        self.router.callback_query.register(self.cbk_account, F.data == "account")
        self.router.callback_query.register(self.cbk_renew, F.data == "renew")
        self.router.callback_query.register(self.cbk_support, F.data == "support")
        self.router.callback_query.register(self.cbk_guide, F.data == "guide")

        # Plan selection + payment flow
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

        # Include router
        self.dp.include_router(self.router)

    # ==========================================================
    # LIFECYCLE
    # ==========================================================
    async def start(self):
        """Start the bot service"""
        if self.logger:
            self.logger.info("🤖 Starting Telegram Bot Service...")

        # Webhook vs Polling
        if self.settings.telegram.webhook_url:
            webhook_url = f"{self.settings.telegram.webhook_url.rstrip('/')}/webhook"
            await self.bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "callback_query", "inline_query"],
            )
            if self.logger:
                self.logger.info(f"🌐 Webhook set to: {webhook_url}")
        else:
            await self.dp.start_polling(
                self.bot,
                handle_signals=False,
                timeout=self.settings.telegram.polling_timeout,
            )

    async def stop(self):
        """Stop the bot service"""
        if self.logger:
            self.logger.info("🛑 Stopping Telegram Bot Service...")
        await self.bot.session.close()

    # ==========================================================
    # COMMAND HANDLERS
    # ==========================================================
    async def cmd_start(self, message: Message):
        """Handle /start command with premium welcome"""
        user = await self.get_or_create_user(message.from_user)
        account = await self.get_user_active_account(user.id)

        if account:
            await self.show_account_dashboard(message, user, account, edit_if_possible=False)
        else:
            await self.show_welcome_message(message, user)

    async def cmd_help(self, message: Message):
        """Handle /help command"""
        help_text = self.ui.generate_help_message()
        keyboard = self.ui.get_help_keyboard()
        await message.answer(help_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    async def cmd_account(self, message: Message):
        """Handle /account command"""
        user = await self.get_or_create_user(message.from_user)
        account = await self.get_user_active_account(user.id)
        if account:
            await self.show_account_dashboard(message, user, account, edit_if_possible=False)
        else:
            await self.show_no_account_message(message)

    async def cmd_admin(self, message: Message):
        """Handle /admin command"""
        if not await self.is_admin(message.from_user.id):
            await message.answer("❌ You don't have admin privileges.")
            return
        await self.show_admin_dashboard(message)

    # ==========================================================
    # CALLBACK HANDLERS (NAV)
    # ==========================================================
    async def cbk_home(self, cq: CallbackQuery):
        user = await self.get_or_create_user(cq.from_user)
        account = await self.get_user_active_account(user.id)
        if account:
            await self.show_account_dashboard(cq.message, user, account, edit_if_possible=True)
        else:
            await self.show_welcome_message(cq.message, user, edit_if_possible=True)
        await cq.answer()

    async def cbk_buy(self, cq: CallbackQuery):
        plans = await self.get_available_plans()
        message = self.ui.generate_plan_selection_message(plans)
        keyboard = self.ui.get_plan_keyboard(plans)  # NOTE: ui.py has get_plan_keyboard
        await cq.message.edit_text(message, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await cq.answer()

    async def cbk_account(self, cq: CallbackQuery):
        # FIX: callback handler exists (sebelum ni crash sebab tak wujud)
        user = await self.get_or_create_user(cq.from_user)
        account = await self.get_user_active_account(user.id)
        if account:
            await self.show_account_dashboard(cq.message, user, account, edit_if_possible=True)
        else:
            await self.show_no_account_message(cq.message, edit_if_possible=True)
        await cq.answer()

    async def cbk_renew(self, cq: CallbackQuery):
        user = await self.get_or_create_user(cq.from_user)
        account = await self.get_user_active_account(user.id)
        if not account:
            await cq.answer("No active account to renew.", show_alert=True)
            return

        msg = "🔄 <b>Renew Subscription</b>\n\nChoose renewal option below:"
        kb = self.ui.get_renew_keyboard()
        await cq.message.edit_text(msg, reply_markup=kb, parse_mode=ParseMode.HTML)
        await cq.answer()

    async def cbk_support(self, cq: CallbackQuery):
        help_text = self.ui.generate_help_message()
        keyboard = self.ui.get_help_keyboard()
        await cq.message.edit_text(help_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await cq.answer()

    async def cbk_guide(self, cq: CallbackQuery):
        # simple guide (can be expanded)
        msg = (
            "🧠 <b>Setup Guide</b>\n\n"
            "1) Install VPN app (v2rayNG / Shadowrocket)\n"
            "2) Tap <b>Copy Config</b> in dashboard\n"
            "3) Import link into the app\n"
            "4) Connect ✅\n\n"
            "Need help? Tap Support."
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="🛟 Support", callback_data="support")
        kb.button(text="🏠 Home", callback_data="home")
        kb.adjust(2)
        await cq.message.edit_text(msg, reply_markup=kb.as_markup(), parse_mode=ParseMode.HTML)
        await cq.answer()

    # ==========================================================
    # CALLBACK HANDLERS (PLAN + PAYMENT)
    # ==========================================================
    async def cbk_plan(self, cq: CallbackQuery):
        plan_code = cq.data.split(":", 1)[1].strip()
        user = await self.get_or_create_user(cq.from_user)

        if plan_code == "trial" and await self.has_used_trial(user.id):
            await self.show_trial_used_message(cq)
            return

        plan = await self.get_plan_by_code(plan_code)
        if not plan:
            await cq.answer("Plan not found!", show_alert=True)
            return

        checkout_message = self.ui.generate_checkout_message(plan, user)
        checkout_keyboard = self.ui.get_checkout_keyboard(plan)  # ui.py has get_checkout_keyboard
        await cq.message.edit_text(checkout_message, reply_markup=checkout_keyboard, parse_mode=ParseMode.HTML)
        await cq.answer()

    async def cbk_pay(self, cq: CallbackQuery):
        plan_code = cq.data.split(":", 1)[1].strip()
        user = await self.get_or_create_user(cq.from_user)

        if plan_code == "trial" and await self.has_used_trial(user.id):
            await self.show_trial_used_message(cq)
            return

        # Create order (DB)
        order = await self.create_order(user, plan_code)
        # payment link
        payment_url = await self.payment_service.create_payment_link(order)

        pending_message = self.ui.generate_payment_pending_message(order, payment_url)
        pending_keyboard = self.ui.get_payment_keyboard(order, payment_url)  # ui.py has get_payment_keyboard

        await cq.message.edit_text(pending_message, reply_markup=pending_keyboard, parse_mode=ParseMode.HTML)
        await cq.answer()

    async def cbk_check_payment(self, cq: CallbackQuery):
        order_id = cq.data.split(":", 1)[1].strip()
        order = await self.get_order_by_id(order_id)

        if not order:
            await cq.answer("Order not found!", show_alert=True)
            return

        is_paid = await self.payment_service.check_payment_status(order)

        if is_paid:
            await self.process_successful_payment(cq, order)
        else:
            await cq.answer("Payment still pending. Complete payment then try again.", show_alert=True)

    async def cbk_cancel(self, cq: CallbackQuery):
        order_id = cq.data.split(":", 1)[1].strip()
        order = await self.get_order_by_id(order_id)
        if not order:
            await cq.answer("Order not found!", show_alert=True)
            return

        await self.cancel_order(order)
        await cq.answer("Cancelled.")
        await self.cbk_home(cq)

    async def cbk_rules(self, cq: CallbackQuery):
        order_id = cq.data.split(":", 1)[1].strip()
        msg = self.ui.generate_rules_message()
        kb = self.ui.get_rules_keyboard(order_id)
        await cq.message.edit_text(msg, reply_markup=kb, parse_mode=ParseMode.HTML)
        await cq.answer()

    async def cbk_agree(self, cq: CallbackQuery):
        order_id = cq.data.split(":", 1)[1].strip()
        order = await self.get_order_by_id(order_id)

        if not order or order.status != PaymentStatus.PAID:
            await cq.answer("Payment not verified!", show_alert=True)
            return

        await self.accept_terms(order)

        # provision VPN
        account = await self.create_vpn_account(order)

        # show dashboard
        user = await self.get_user_by_id(order.user_id)
        await self.show_account_dashboard(cq.message, user, account, edit_if_possible=True)
        await cq.answer("✅ Activated!")

    # ==========================================================
    # CALLBACK HANDLERS (ACCOUNT)
    # ==========================================================
    async def cbk_copy_config(self, cq: CallbackQuery):
        user = await self.get_or_create_user(cq.from_user)
        account = await self.get_user_active_account(user.id)
        if not account:
            await cq.answer("No active account!", show_alert=True)
            return

        links = getattr(account, "config_links", {}) or {}
        # IMPORTANT: user wants VLESS NTLS only (so prioritize it)
        # fallback if model stores different key names
        filtered = {}
        for key in ("vless_ntls", "VLESS_NTLS", "vlessNTLS"):
            if key in links and links[key]:
                filtered["vless_ntls"] = links[key]
                break
        if not filtered and links:
            # if only one link exists, still send it
            first_k = next(iter(links.keys()))
            filtered[first_k] = links[first_k]

        msg = self.ui.generate_config_message(account, filtered)
        await cq.message.answer(msg, parse_mode=ParseMode.HTML)
        await cq.answer("✅ Config sent!")

    async def cbk_qr_config(self, cq: CallbackQuery):
        user = await self.get_or_create_user(cq.from_user)
        account = await self.get_user_active_account(user.id)
        if not account:
            await cq.answer("No active account!", show_alert=True)
            return

        links = getattr(account, "config_links", {}) or {}
        primary = links.get("vless_ntls") or links.get("vless_tls") or ""
        if not primary:
            await cq.answer("No config link found.", show_alert=True)
            return

        qr_bytes = generate_qr_code(primary)
        await cq.message.answer_photo(
            BufferedInputFile(qr_bytes, filename="config_qr.png"),
            caption="📱 Scan this QR code with your VPN app",
        )
        await cq.answer("✅ QR sent!")

    async def cbk_speed_test(self, cq: CallbackQuery):
        # placeholder (optional implement)
        await cq.answer("Speed test feature coming soon.", show_alert=True)

    async def cbk_switch_server(self, cq: CallbackQuery):
        # placeholder (optional implement)
        await cq.answer("Switch server feature coming soon.", show_alert=True)

    # ==========================================================
    # SUPPORT
    # ==========================================================
    async def cbk_open_ticket(self, cq: CallbackQuery):
        user = await self.get_or_create_user(cq.from_user)
        await self.set_user_state(user.id, "awaiting_ticket_description")
        msg = self.ui.generate_ticket_instructions()
        await cq.message.answer(msg, parse_mode=ParseMode.HTML)
        await cq.answer()

    async def cbk_view_tickets(self, cq: CallbackQuery):
        user = await self.get_or_create_user(cq.from_user)
        tickets = await self.get_user_tickets(user.id)
        if not tickets:
            await cq.answer("No tickets yet.", show_alert=True)
            return

        text_lines = ["🎫 <b>Your Tickets</b>\n"]
        for t in tickets[:10]:
            text_lines.append(f"• <code>{t.ticket_id}</code> — {t.status.value}")
        kb = InlineKeyboardBuilder()
        kb.button(text="🏠 Home", callback_data="home")
        await cq.message.edit_text("\n".join(text_lines), reply_markup=kb.as_markup(), parse_mode=ParseMode.HTML)
        await cq.answer()

    # ==========================================================
    # UI PAGES
    # ==========================================================
    async def show_welcome_message(self, message: Message, user: User, edit_if_possible: bool = False):
        welcome_text = self.ui.generate_welcome_message(user)
        welcome_keyboard = self.ui.get_welcome_keyboard()
        if edit_if_possible and hasattr(message, "edit_text"):
            try:
                await message.edit_text(welcome_text, reply_markup=welcome_keyboard, parse_mode=ParseMode.HTML)
                return
            except Exception:
                pass
        await message.answer(welcome_text, reply_markup=welcome_keyboard, parse_mode=ParseMode.HTML)

    async def show_account_dashboard(self, message: Message, user: User, account: Account, edit_if_possible: bool = True):
        dashboard_text = self.ui.generate_dashboard_message(user, account)
        dashboard_keyboard = self.ui.get_dashboard_keyboard(account)
        if edit_if_possible and hasattr(message, "edit_text"):
            try:
                await message.edit_text(dashboard_text, reply_markup=dashboard_keyboard, parse_mode=ParseMode.HTML)
                return
            except Exception:
                pass
        await message.answer(dashboard_text, reply_markup=dashboard_keyboard, parse_mode=ParseMode.HTML)

    async def show_no_account_message(self, message: Message, edit_if_possible: bool = False):
        msg = (
            "❌ <b>No active VPN account</b>\n\n"
            "Tap <b>Buy VPN</b> to get started."
        )
        kb = self.ui.get_welcome_keyboard()
        if edit_if_possible:
            try:
                await message.edit_text(msg, reply_markup=kb, parse_mode=ParseMode.HTML)
                return
            except Exception:
                pass
        await message.answer(msg, reply_markup=kb, parse_mode=ParseMode.HTML)

    async def show_trial_used_message(self, cq: CallbackQuery):
        await cq.answer("⚠️ Trial already used on this account.", show_alert=True)

    async def show_admin_dashboard(self, message: Message):
        stats = await self.get_admin_stats()
        admin_text = self.ui.generate_admin_dashboard(stats)
        admin_keyboard = self.ui.get_admin_keyboard()
        await message.answer(admin_text, reply_markup=admin_keyboard, parse_mode=ParseMode.HTML)

    # ==========================================================
    # ADMIN COMMANDS
    # ==========================================================
    async def admin_broadcast(self, message: Message):
        if not await self.is_admin(message.from_user.id):
            return

        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await message.answer("Usage: /broadcast <message>")
            return

        sent = await self.send_broadcast(parts[1].strip())
        await message.answer(f"📢 Broadcast sent to {sent} users")

    async def admin_servers(self, message: Message):
        if not await self.is_admin(message.from_user.id):
            return
        servers = await self.get_all_servers()
        txt = self.ui.generate_servers_status(servers)
        await message.answer(txt, parse_mode=ParseMode.HTML)

    async def admin_users(self, message: Message):
        if not await self.is_admin(message.from_user.id):
            return
        total = await self.count_users()
        await message.answer(f"👥 Total users: <b>{total}</b>", parse_mode=ParseMode.HTML)

    async def admin_stats(self, message: Message):
        if not await self.is_admin(message.from_user.id):
            return
        stats = await self.get_admin_stats()
        txt = self.ui.generate_stats_message(stats)
        await message.answer(txt, parse_mode=ParseMode.HTML)

    # ==========================================================
    # DB / STATE HELPERS (COMPATIBLE WITH db.session())
    # ==========================================================
    async def get_or_create_user(self, tg_user) -> User:
        async with self.db.session() as session:
            res = await session.execute(select(User).where(User.telegram_id == tg_user.id))
            user = res.scalar_one_or_none()
            if not user:
                user = User(
                    telegram_id=tg_user.id,
                    username=tg_user.username,
                    first_name=tg_user.first_name,
                    last_name=tg_user.last_name,
                )
                session.add(user)
            return user

    async def get_user_by_id(self, user_id: int) -> User:
        async with self.db.session() as session:
            res = await session.execute(select(User).where(User.id == user_id))
            return res.scalar_one()

    async def get_user_active_account(self, user_id: int) -> Optional[Account]:
        async with self.db.session() as session:
            res = await session.execute(
                select(Account)
                .where(
                    Account.user_id == user_id,
                    Account.status == AccountStatus.ACTIVE,
                    Account.expires_at > datetime.utcnow(),
                )
                .order_by(Account.expires_at.desc())
                .limit(1)
            )
            return res.scalar_one_or_none()

    async def get_available_plans(self) -> List[Plan]:
        async with self.db.session() as session:
            res = await session.execute(
                select(Plan).where(Plan.is_active == True).order_by(Plan.price.asc())
            )
            return list(res.scalars().all())

    async def get_plan_by_code(self, code: str) -> Optional[Plan]:
        async with self.db.session() as session:
            # PlanType value usually matches code ("trial"/"premium")
            res = await session.execute(select(Plan).where(Plan.type == PlanType(code)))
            return res.scalar_one_or_none()

    async def has_used_trial(self, user_id: int) -> bool:
        async with self.db.session() as session:
            res = await session.execute(
                select(Account)
                .where(Account.user_id == user_id, Account.plan_type == PlanType.TRIAL)  # adjust if your model differs
                .limit(1)
            )
            return res.scalar_one_or_none() is not None

    async def create_order(self, user: User, plan_code: str) -> Order:
        plan = await self.get_plan_by_code(plan_code)
        if not plan:
            raise ValueError("Plan not found")

        order = Order(
            order_id=str(uuid4()),
            user_id=user.id,
            plan_id=plan.id,
            amount=float(plan.price),
            currency="MYR",
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        async with self.db.session() as session:
            session.add(order)
        return order

    async def get_order_by_id(self, order_id: str) -> Optional[Order]:
        async with self.db.session() as session:
            res = await session.execute(select(Order).where(Order.order_id == order_id))
            return res.scalar_one_or_none()

    async def cancel_order(self, order: Order):
        async with self.db.session() as session:
            res = await session.execute(select(Order).where(Order.id == order.id))
            o = res.scalar_one()
            o.status = PaymentStatus.CANCELLED

    async def accept_terms(self, order: Order):
        async with self.db.session() as session:
            res = await session.execute(select(Order).where(Order.id == order.id))
            o = res.scalar_one()
            o.terms_accepted = True  # if your model has it

    async def process_successful_payment(self, cq: CallbackQuery, order: Order):
        # Mark paid
        async with self.db.session() as session:
            res = await session.execute(select(Order).where(Order.id == order.id))
            o = res.scalar_one()
            o.status = PaymentStatus.PAID
            o.paid_at = datetime.utcnow()

        # Show rules first (require user click agree)
        msg = self.ui.generate_rules_message()
        kb = self.ui.get_rules_keyboard(order.order_id)
        await cq.message.edit_text(msg, reply_markup=kb, parse_mode=ParseMode.HTML)
        await cq.answer("✅ Payment verified!", show_alert=True)

    async def create_vpn_account(self, order: Order) -> Account:
        # Provisioning via VPN service
        # (Implement inside your VPNProvisioningService)
        account = await self.vpn_service.provision_from_order(order)
        return account

    async def get_user_tickets(self, user_id: int) -> List[Ticket]:
        async with self.db.session() as session:
            res = await session.execute(
                select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.created_at.desc())
            )
            return list(res.scalars().all())

    async def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in (self.settings.telegram.admin_ids or [])

    # ==========================================================
    # USER STATE (Redis optional)
    # ==========================================================
    def _redis_enabled(self) -> bool:
        return bool(getattr(self.settings, "redis_enabled", True)) and getattr(self.db, "redis_client", None) is not None

    async def set_user_state(self, user_id: int, state: str, data: Optional[Dict[str, Any]] = None):
        payload = {"state": state, "updated_at": datetime.utcnow().isoformat()}
        if data:
            payload.update(data)

        if self._redis_enabled():
            try:
                await self.db.redis_client.setex(f"user_state:{user_id}", 1800, json.dumps(payload))
                return
            except Exception:
                pass

        # fallback
        self._state_mem[user_id] = payload

    async def get_user_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        if self._redis_enabled():
            try:
                raw = await self.db.redis_client.get(f"user_state:{user_id}")
                if raw:
                    return json.loads(raw)
            except Exception:
                pass
        return self._state_mem.get(user_id)

    async def clear_user_state(self, user_id: int):
        if self._redis_enabled():
            try:
                await self.db.redis_client.delete(f"user_state:{user_id}")
            except Exception:
                pass
        self._state_mem.pop(user_id, None)

    # ==========================================================
    # ADMIN UTILS
    # ==========================================================
    async def send_broadcast(self, text_msg: str) -> int:
        count = 0
        async with self.db.session() as session:
            res = await session.execute(select(User.telegram_id))
            ids = [x for x in res.scalars().all() if x]
        for tg_id in ids:
            try:
                await self.bot.send_message(tg_id, text_msg, parse_mode=ParseMode.HTML)
                count += 1
                await asyncio.sleep(0.05)
            except Exception:
                continue
        return count

    async def count_users(self) -> int:
        async with self.db.session() as session:
            res = await session.execute(text("SELECT COUNT(*) FROM users"))
            return int(res.scalar() or 0)

    async def get_all_servers(self) -> List[Server]:
        async with self.db.session() as session:
            res = await session.execute(select(Server).order_by(Server.name.asc()))
            return list(res.scalars().all())

    async def get_admin_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        async with self.db.session() as session:
            res = await session.execute(text("SELECT COUNT(*) FROM users"))
            stats["total_users"] = int(res.scalar() or 0)

            res = await session.execute(text("SELECT COUNT(*) FROM accounts WHERE status='active'"))
            stats["active_accounts"] = int(res.scalar() or 0)

            res = await session.execute(text("SELECT COALESCE(SUM(amount),0) FROM orders WHERE status='paid'"))
            stats["total_revenue"] = float(res.scalar() or 0)

            res = await session.execute(text("SELECT COUNT(*) FROM servers WHERE status='online'"))
            stats["servers_online"] = int(res.scalar() or 0)

            res = await session.execute(text("SELECT COUNT(*) FROM tickets WHERE status='pending'"))
            stats["pending_tickets"] = int(res.scalar() or 0)

        # system load optional
        stats["system_load"] = 0.0
        return stats

    # ==========================================================
    # BACKGROUND TASKS (optional call from main)
    # ==========================================================
    async def start_background_tasks(self):
        tasks = [
            self.expiry_reminder_task(),
            self.health_check_task(),
            self.cleanup_task(),
        ]
        await asyncio.gather(*tasks)

    async def expiry_reminder_task(self):
        while True:
            try:
                await asyncio.sleep(3600)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"expiry_reminder_task error: {e}")
                await asyncio.sleep(300)

    async def health_check_task(self):
        while True:
            try:
                await asyncio.sleep(300)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"health_check_task error: {e}")
                await asyncio.sleep(60)

    async def cleanup_task(self):
        while True:
            try:
                await asyncio.sleep(86400)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"cleanup_task error: {e}")
                await asyncio.sleep(3600)
