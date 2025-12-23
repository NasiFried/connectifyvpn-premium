"""
SQLAlchemy models for ConnectifyVPN Premium Suite
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean, DateTime, Text, Float, 
    ForeignKey, JSON, Enum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum


Base = declarative_base()


# Enums
class UserStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"


class PlanType(enum.Enum):
    TRIAL = "trial"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class PaymentStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class AccountStatus(enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    LOCKED = "locked"


class ServerStatus(enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    OVERLOADED = "overloaded"


class TicketStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class NotificationType(enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    TELEGRAM = "telegram"


class VPNProtocol(enum.Enum):
    VLESS = "vless"
    VMESS = "vmess"
    TROJAN = "trojan"
    SHADOWSOCKS = "shadowsocks"


# Models
class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True))
    
    # Relationships
    accounts = relationship("Account", back_populates="user")
    orders = relationship("Order", back_populates="user")
    tickets = relationship("Ticket", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"
    
    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return self.username
        else:
            return f"User {self.telegram_id}"


class Plan(Base):
    """Subscription plans"""
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(Enum(PlanType), nullable=False)
    
    price = Column(Float, nullable=False)  # Price in RM
    duration_days = Column(Integer, nullable=False)
    device_limit = Column(Integer, default=1, nullable=False)
    
    features = Column(JSON, default=dict)  # JSON with plan features
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    orders = relationship("Order", back_populates="plan")
    
    def __repr__(self):
        return f"<Plan(id={self.id}, name={self.name}, type={self.type}, price={self.price})>"
    
    @property
    def display_price(self) -> str:
        return f"RM {self.price:.2f}"
    
    @property
    def is_trial(self) -> bool:
        return self.type == PlanType.TRIAL


class Server(Base):
    """VPN servers"""
    __tablename__ = "servers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=False)
    location = Column(String(100), nullable=True)
    
    status = Column(Enum(ServerStatus), default=ServerStatus.ONLINE, nullable=False)
    capacity = Column(Integer, default=20, nullable=False)
    
    # Server specs
    cpu_cores = Column(Integer, nullable=True)
    memory_gb = Column(Float, nullable=True)
    bandwidth_gb = Column(Float, nullable=True)
    
    # Performance metrics
    current_load = Column(Float, default=0.0, nullable=False)
    active_connections = Column(Integer, default=0, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    
    # SSH configuration
    ssh_port = Column(Integer, default=22, nullable=False)
    ssh_user = Column(String(50), default="root", nullable=False)
    
    # Configuration
    config = Column(JSON, default=dict)  # Server-specific config
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_check_at = Column(DateTime(timezone=True))
    
    # Relationships
    accounts = relationship("Account", back_populates="server")
    
    def __repr__(self):
        return f"<Server(id={self.id}, name={self.name}, hostname={self.hostname})>"
    
    @property
    def utilization_percent(self) -> float:
        if self.capacity == 0:
            return 0.0
        return (self.active_connections / self.capacity) * 100
    
    @property
    def is_available(self) -> bool:
        return (
            self.status == ServerStatus.ONLINE and
            self.utilization_percent < 90
        )


class Account(Base):
    """User VPN accounts"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False, index=True)
    
    # VPN credentials
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=True)
    
    # Configuration
    protocol = Column(Enum(VPNProtocol), default=VPNProtocol.VLESS, nullable=False)
    config = Column(JSON, default=dict)  # Full VPN config
    
    # Status
    status = Column(Enum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False)
    
    # Subscription details
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Usage tracking
    data_used_gb = Column(Float, default=0.0, nullable=False)
    data_limit_gb = Column(Float, nullable=True)  # None = unlimited
    
    # Device tracking
    device_limit = Column(Integer, default=1, nullable=False)
    active_devices = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    server = relationship("Server", back_populates="accounts")
    plan = relationship("Plan")
    sessions = relationship("VPNSession", back_populates="account")
    
    def __repr__(self):
        return f"<Account(id={self.id}, user_id={self.user_id}, username={self.username})>"
    
    @property
    def is_expired(self) -> bool:
        return self.expires_at < datetime.utcnow()
    
    @property
    def days_until_expiry(self) -> int:
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def config_links(self) -> Dict[str, str]:
        """Generate VPN configuration links"""
        links = {}
        
        if self.protocol == VPNProtocol.VLESS:
            # VLESS TLS
            if self.config.get("tls_port"):
                links["vless_tls"] = (
                    f"vless://{self.uuid}@{self.server.hostname}:{self.config['tls_port']}"
                    f"?path={self.config.get('ws_path', '/vless')}"
                    f"&security=tls&encryption=none&type=ws"
                    f"#{self.username}"
                )
            
            # VLESS NTLS
            if self.config.get("ntls_port"):
                links["vless_ntls"] = (
                    f"vless://{self.uuid}@{self.server.hostname}:{self.config['ntls_port']}"
                    f"?path={self.config.get('ws_path', '/vless')}"
                    f"&encryption=none&type=ws"
                    f"#{self.username}"
                )
        
        return links


class Order(Base):
    """Payment orders"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    
    # Payment details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="MYR", nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Gateway info
    gateway = Column(String(50), nullable=False)  # toyyibpay, stripe, etc
    gateway_reference = Column(String(255), nullable=True)  # bill_code, etc
    gateway_response = Column(JSON, nullable=True)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    plan = relationship("Plan", back_populates="orders")
    
    def __repr__(self):
        return f"<Order(id={self.id}, order_id={self.order_id}, status={self.status})>"
    
    @property
    def is_paid(self) -> bool:
        return self.status == PaymentStatus.PAID


class VPNSession(Base):
    """VPN connection sessions"""
    __tablename__ = "vpn_sessions"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    
    # Connection info
    client_ip = Column(String(45), nullable=False)
    server_ip = Column(String(45), nullable=False)
    protocol = Column(Enum(VPNProtocol), nullable=False)
    
    # Session tracking
    connected_at = Column(DateTime(timezone=True), server_default=func.now())
    disconnected_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage
    bytes_sent = Column(BigInteger, default=0, nullable=False)
    bytes_received = Column(BigInteger, default=0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    disconnect_reason = Column(String(255), nullable=True)
    
    # Relationships
    account = relationship("Account", back_populates="sessions")
    
    def __repr__(self):
        return f"<VPNSession(id={self.id}, account_id={self.account_id}, active={self.is_active})>"
    
    @property
    def duration_seconds(self) -> Optional[int]:
        if self.disconnected_at:
            return int((self.disconnected_at - self.connected_at).total_seconds())
        elif self.is_active:
            return int((datetime.utcnow() - self.connected_at).total_seconds())
        return None
    
    @property
    def total_bytes(self) -> int:
        return self.bytes_sent + self.bytes_received
    
    @property
    def total_gb(self) -> float:
        return self.total_bytes / (1024 ** 3)


class Ticket(Base):
    """Support tickets"""
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True)
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Ticket info
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    priority = Column(String(20), default="medium", nullable=False)
    
    # Category
    category = Column(String(50), nullable=True)
    tags = Column(ARRAY(String), default=list)
    
    # Admin response
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    response = Column(Text, nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="tickets")
    admin = relationship("User", foreign_keys=[admin_id])
    
    def __repr__(self):
        return f"<Ticket(id={self.id}, ticket_number={self.ticket_number}, status={self.status})>"


class Notification(Base):
    """Notification queue"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Notification info
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Delivery tracking
    is_sent = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    failed_attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type})>"


class UserSession(Base):
    """User sessions"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Session tracking
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(String(500), nullable=True)
    
    # Device info
    device_type = Column(String(50), nullable=True)
    device_os = Column(String(50), nullable=True)
    device_browser = Column(String(50), nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class AuditLog(Base):
    """Audit logging for security compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Event tracking
    event_type = Column(String(100), nullable=False, index=True)
    event_description = Column(Text, nullable=False)
    
    # Context
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(String(500), nullable=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    
    # Additional data
    metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, event_type={self.event_type})>"


class SystemMetric(Base):
    """System performance metrics"""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True)
    metric_type = Column(String(50), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    labels = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<SystemMetric(id={self.id}, type={self.metric_type}, value={self.metric_value})>"


# Indexes for performance
Index('idx_users_telegram_id', User.telegram_id)
Index('idx_users_email', User.email)
Index('idx_accounts_user_id_status', Account.user_id, Account.status)
Index('idx_accounts_expires_at', Account.expires_at)
Index('idx_orders_user_id_status', Order.user_id, Order.status)
Index('idx_vpn_sessions_account_id_active', VPNSession.account_id, VPNSession.is_active)
Index('idx_tickets_user_id_status', Ticket.user_id, Ticket.status)
Index('idx_audit_logs_user_id_created_at', AuditLog.user_id, AuditLog.created_at)
Index('idx_system_metrics_type_created_at', SystemMetric.metric_type, SystemMetric.created_at)
