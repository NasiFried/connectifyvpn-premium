#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ConnectifyVPN Premium Suite
===========================

Sistem VPN premium yang lengkap dengan automasi penuh,
UI/UX bertaraf enterprise, dan skalabilitas tinggi.

Author: Premium Development Team
Version: 1.0.0
License: Commercial

Fitur Utama:
-----------
✅ Automasi provisioning Xray (VLESS/VMess/Trojan)
✅ Payment gateway integration (ToyyibPay, Stripe, Crypto)
✅ Smart server selection & load balancing
✅ Real-time monitoring & analytics
✅ Advanced user management
✅ Multi-protocol support
✅ Premium UI/UX dengan glassmorphism
✅ Mobile-responsive design
✅ Admin dashboard lengkap
✅ Notification system (Email, SMS, Push)
✅ Auto-scaling & failover
✅ Comprehensive audit logging
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import Settings
from core.database import DatabaseManager
from core.logging import setup_logging
from services.bot import TelegramBotService
from services.api import APIService
from services.vpn import VPNProvisioningService
from services.payment import PaymentService
from services.notification import NotificationService
from services.analytics import AnalyticsService
from services.admin import AdminService
from utils.migrations import run_migrations


class ConnectifyVPN:
    """
    Main application class for ConnectifyVPN Premium Suite
    """
    
    def __init__(self):
        self.settings = Settings()
        self.db = DatabaseManager(self.settings)
        self.logger = setup_logging()
        
        # Initialize services
        self.bot_service = TelegramBotService(self.settings, self.db)
        self.api_service = APIService(self.settings, self.db)
        self.vpn_service = VPNProvisioningService(self.settings, self.db)
        self.payment_service = PaymentService(self.settings, self.db)
        self.notification_service = NotificationService(self.settings, self.db)
        self.analytics_service = AnalyticsService(self.settings, self.db)
        self.admin_service = AdminService(self.settings, self.db)
        
    async def initialize(self):
        """Initialize all services and dependencies"""
        self.logger.info("🚀 Initializing ConnectifyVPN Premium Suite...")
        
        # Run database migrations
        await run_migrations(self.db)
        
        # Initialize services
        await self.db.initialize()
        await self.vpn_service.initialize()
        await self.payment_service.initialize()
        await self.notification_service.initialize()
        await self.analytics_service.initialize()
        
        self.logger.info("✅ All services initialized successfully")
        
    async def start(self):
        """Start all services"""
        self.logger.info("🚀 Starting ConnectifyVPN Premium Suite...")
        
        try:
            # Start services concurrently
            tasks = [
                self.bot_service.start(),
                self.api_service.start(),
                self.vpn_service.start(),
                self.payment_service.start(),
                self.notification_service.start(),
                self.analytics_service.start(),
                self.admin_service.start()
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"❌ Error starting services: {e}")
            raise
            
    async def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("🛑 Shutting down ConnectifyVPN Premium Suite...")
        
        tasks = [
            self.bot_service.stop(),
            self.api_service.stop(),
            self.vpn_service.stop(),
            self.payment_service.stop(),
            self.notification_service.stop(),
            self.analytics_service.stop(),
            self.admin_service.stop(),
            self.db.close()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("✅ Shutdown complete")


async def main():
    """Main entry point"""
    app = ConnectifyVPN()
    
    try:
        await app.initialize()
        await app.start()
        
        # Keep running
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Received shutdown signal")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        await app.shutdown()


if __name__ == "__main__":
    # Check if running in correct directory
    if not Path("config/.env").exists():
        print("❌ Error: config/.env not found!")
        print("💡 Please ensure you're running from the project root directory")
        sys.exit(1)
        
    print("""
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                    ConnectifyVPN Premium Suite v1.0.0                        ║
    ║                    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                          ║
    ║                                                                               ║
    ║  ⚡ Secure. Fast. Unlimited.                                                  ║
    ║  🌐 Redefining Digital Freedom                                               ║
    ║                                                                               ║
    ║  Starting premium VPN automation system...                                  ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())
