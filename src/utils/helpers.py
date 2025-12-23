"""
Helper utilities for ConnectifyVPN Premium Suite
"""

import asyncio
import json
import re
import secrets
import string
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union
from uuid import UUID, uuid4

import aiohttp
import qrcode
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO


def format_currency(amount: float, currency: str = "MYR") -> str:
    """Format currency with proper decimal places"""
    return f"{currency} {amount:.2f}"


def format_date(date: datetime, format_str: str = "%d %b %Y") -> str:
    """Format date in user-friendly format"""
    return date.strftime(format_str)


def format_datetime(date: datetime, format_str: str = "%d %b %Y %H:%M") -> str:
    """Format datetime in user-friendly format"""
    return date.strftime(format_str)


def format_duration(seconds: int) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    elif seconds < 86400:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"


def format_bytes(bytes_count: int) -> str:
    """Format bytes in human-readable format"""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 ** 2:
        return f"{bytes_count / 1024:.2f} KB"
    elif bytes_count < 1024 ** 3:
        return f"{bytes_count / (1024 ** 2):.2f} MB"
    elif bytes_count < 1024 ** 4:
        return f"{bytes_count / (1024 ** 3):.2f} GB"
    else:
        return f"{bytes_count / (1024 ** 4):.2f} TB"


def generate_id(prefix: str = "", length: int = 8) -> str:
    """Generate unique ID with prefix"""
    alphabet = string.ascii_uppercase + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}{random_part}" if prefix else random_part


def generate_uuid() -> str:
    """Generate UUID string"""
    return str(uuid4())


def generate_password(length: int = 12) -> str:
    """Generate secure password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_otp(length: int = 6) -> str:
    """Generate numeric OTP"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def generate_qr_code(data: str, size: int = 256) -> bytes:
    """Generate QR code image"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def generate_premium_qr_code(data: str, size: int = 256, 
                           primary_color: str = "#16213e",
                           secondary_color: str = "#e94560") -> bytes:
    """Generate premium styled QR code"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color=primary_color, back_color="white")
    
    # Add premium styling
    draw = ImageDraw.Draw(img)
    
    # Add border
    width, height = img.size
    border_color = secondary_color
    border_width = 4
    draw.rectangle(
        [0, 0, width-1, height-1],
        outline=border_color,
        width=border_width
    )
    
    # Resize
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    # Remove spaces and dashes
    phone = phone.replace(" ", "").replace("-", "")
    
    # Check for Malaysian format
    malaysian_pattern = r'^(\+?60|0)[1-9][0-9]{8,9}$'
    if re.match(malaysian_pattern, phone):
        return True
        
    # Generic international format
    international_pattern = r'^\+[1-9][0-9]{6,14}$'
    return re.match(international_pattern, phone) is not None


def validate_username(username: str) -> bool:
    """Validate username format"""
    if len(username) < 3 or len(username) > 30:
        return False
    
    pattern = r'^[a-zA-Z0-9_]+$'
    return re.match(pattern, username) is not None


def sanitize_html(text: str) -> str:
    """Sanitize HTML tags"""
    return re.sub(r'<[^>]+>', '', text)


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def slugify(text: str) -> str:
    """Convert text to URL slug"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    return text


def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def clean_phone_number(phone: str) -> str:
    """Clean and format phone number"""
    # Remove all non-digit characters
    phone = re.sub(r'[^\d+]', '', phone)
    
    # Add Malaysian country code if needed
    if phone.startswith('0'):
        phone = '+60' + phone[1:]
    elif not phone.startswith('+') and len(phone) >= 10:
        phone = '+' + phone
        
    return phone


def format_phone_number(phone: str) -> str:
    """Format phone number for display"""
    phone = clean_phone_number(phone)
    
    if phone.startswith('+60'):
        # Malaysian format
        return phone[:3] + ' ' + phone[3:5] + ' ' + phone[5:]
    else:
        # Generic format
        return phone


def parse_config_link(link: str) -> Dict[str, Any]:
    """Parse VPN configuration link"""
    # VLESS link format: vless://uuid@host:port?params#name
    # VMess link format: vmess://base64_json
    # Trojan link format: trojan://password@host:port?params#name
    
    config = {}
    
    if link.startswith('vless://'):
        # Parse VLESS
        parts = link[8:].split('@')
        if len(parts) == 2:
            config['uuid'] = parts[0]
            
            host_port = parts[1].split('?')
            if len(host_port) == 2:
                host_port_parts = host_port[0].split(':')
                if len(host_port_parts) == 2:
                    config['host'] = host_port_parts[0]
                    config['port'] = int(host_port_parts[1])
                    
                # Parse parameters
                params = host_port[1].split('#')[0] if '#' in host_port[1] else host_port[1]
                for param in params.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        config[key] = value
                        
    elif link.startswith('vmess://'):
        # Parse VMess (base64 encoded JSON)
        import base64
        try:
            json_str = base64.b64decode(link[8:]).decode('utf-8')
            config = json.loads(json_str)
        except Exception:
            pass
            
    elif link.startswith('trojan://'):
        # Parse Trojan
        parts = link[9:].split('@')
        if len(parts) == 2:
            config['password'] = parts[0]
            
            host_port = parts[1].split('?')
            if len(host_port) == 2:
                host_port_parts = host_port[0].split(':')
                if len(host_port_parts) == 2:
                    config['host'] = host_port_parts[0]
                    config['port'] = int(host_port_parts[1])
                    
    return config


def generate_config_name(username: str, protocol: str, server_name: str) -> str:
    """Generate configuration name"""
    return f"{username}-{protocol.upper()}-{server_name}"


def calculate_expiry_date(days: int, from_date: Optional[datetime] = None) -> datetime:
    """Calculate expiry date"""
    if from_date is None:
        from_date = datetime.utcnow()
    return from_date + timedelta(days=days)


def days_until_expiry(expiry_date: datetime) -> int:
    """Calculate days until expiry"""
    delta = expiry_date - datetime.utcnow()
    return max(0, delta.days)


def is_expired(expiry_date: datetime) -> bool:
    """Check if subscription is expired"""
    return datetime.utcnow() > expiry_date


def is_near_expiry(expiry_date: datetime, days: int = 7) -> bool:
    """Check if subscription is near expiry"""
    delta = expiry_date - datetime.utcnow()
    return 0 < delta.days <= days


def calculate_discount(original_price: float, discount_percent: float) -> float:
    """Calculate discounted price"""
    return original_price * (1 - discount_percent / 100)


def calculate_tax(amount: float, tax_rate: float = 0.0) -> float:
    """Calculate tax amount"""
    return amount * tax_rate


def calculate_total(amount: float, tax_rate: float = 0.0, discount: float = 0.0) -> float:
    """Calculate total amount"""
    discounted = amount - discount
    tax = calculate_tax(discounted, tax_rate)
    return discounted + tax


def generate_invoice_number() -> str:
    """Generate invoice number"""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    random_part = secrets.token_hex(4).upper()
    return f"INV-{date_str}-{random_part}"


def generate_order_number() -> str:
    """Generate order number"""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    random_part = secrets.token_hex(3).upper()
    return f"ORD-{date_str}-{random_part}"


def generate_ticket_number() -> str:
    """Generate ticket number"""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    random_part = secrets.token_hex(3).upper()
    return f"TKT-{date_str}-{random_part}"


def mask_sensitive_info(text: str, visible_chars: int = 4) -> str:
    """Mask sensitive information"""
    if len(text) <= visible_chars * 2:
        return "*" * len(text)
    
    return text[:visible_chars] + "*" * (len(text) - visible_chars * 2) + text[-visible_chars:]


def generate_random_string(length: int = 8, charset: str = None) -> str:
    """Generate random string"""
    if charset is None:
        charset = string.ascii_letters + string.digits
    return ''.join(secrets.choice(charset) for _ in range(length))


def is_valid_uuid(uuid_str: str) -> bool:
    """Check if string is valid UUID"""
    try:
        UUID(uuid_str)
        return True
    except ValueError:
        return False


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert to integer"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert to float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_json_loads(text: str, default: Dict = None) -> Dict:
    """Safely load JSON"""
    if default is None:
        default = {}
        
    try:
        return json.loads(text) if text else default
    except json.JSONDecodeError:
        return default


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division with default value"""
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ValueError):
        return default


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max"""
    return max(min_val, min(value, max_val))


def interpolate_value(start: float, end: float, factor: float) -> float:
    """Interpolate between two values"""
    return start + (end - start) * clamp_value(factor, 0.0, 1.0)


def weighted_average(values: List[float], weights: List[float]) -> float:
    """Calculate weighted average"""
    if not values or not weights or len(values) != len(weights):
        return 0.0
        
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
        
    return sum(v * w for v, w in zip(values, weights)) / total_weight


def percentile(values: List[float], p: float) -> float:
    """Calculate percentile"""
    if not values:
        return 0.0
        
    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * p
    
    if index.is_integer():
        return sorted_values[int(index)]
    else:
        lower = sorted_values[int(index)]
        upper = sorted_values[int(index) + 1]
        return lower + (upper - lower) * (index % 1)


async def fetch_json(url: str, headers: Optional[Dict] = None, timeout: int = 30) -> Dict:
    """Fetch JSON from URL"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=timeout) as response:
            response.raise_for_status()
            return await response.json()


async def post_json(url: str, data: Dict, headers: Optional[Dict] = None, timeout: int = 30) -> Dict:
    """Post JSON to URL"""
    if headers is None:
        headers = {"Content-Type": "application/json"}
    else:
        headers = headers.copy()
        headers["Content-Type"] = "application/json"
        
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers, timeout=timeout) as response:
            response.raise_for_status()
            return await response.json()


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
            
    return result


def get_nested_value(data: Dict, path: str, default: Any = None) -> Any:
    """Get nested dictionary value using dot notation"""
    keys = path.split(".")
    value = data
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
            
    return value


def set_nested_value(data: Dict, path: str, value: Any) -> None:
    """Set nested dictionary value using dot notation"""
    keys = path.split(".")
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
        
    current[keys[-1]] = value


def chunk_list(items: List, chunk_size: int) -> List[List]:
    """Split list into chunks"""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def find_duplicates(items: List) -> List:
    """Find duplicate items in list"""
    seen = set()
    duplicates = set()
    
    for item in items:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
        
    return list(duplicates)


def remove_duplicates(items: List, preserve_order: bool = True) -> List:
    """Remove duplicates from list"""
    if preserve_order:
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
    else:
        return list(set(items))
