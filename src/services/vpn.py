import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Dict

class VPNProvisioningService:
    """Provision VLESS users on VPS (v4-main style) — NTLS only."""

    def __init__(self, settings, db):
        self.settings = settings
        self.db = db

    async def initialize(self):
        return

    async def start(self):
        return

    async def stop(self):
        return

    async def _ssh(self, host: str, cmd: str, user: str, port: int, key_path: str):
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-i", key_path, "-p", str(port),
            f"{user}@{host}", cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        return proc.returncode, out.decode(errors="ignore"), err.decode(errors="ignore")

    async def create_vless_ntls(
        self,
        *,
        host: str,
        ssh_user: str,
        ssh_port: int,
        ssh_key_path: str,
        username: str,
        uuid: str,
        days: int
    ) -> Dict[str, str]:
        exp_date = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")
        remote = f"""set -e
DOMAIN="$(cat /etc/xray/domain 2>/dev/null || echo {host})"
NTLS="$(grep -w "Vless None TLS" -m1 ~/log-install.txt 2>/dev/null | cut -d: -f2 | tr -d ' ' || true)"
[ -z "$NTLS" ] && NTLS="80"
grep -q "#vless$" /etc/xray/config.json
if grep -q -w "{username}" /etc/xray/config.json; then echo "ERR_USER_EXISTS"; exit 3; fi
sed -i '/#vless$/a\\#& {username} {exp_date}\\\\\\n}},{{"id":"{uuid}","email":"{username}"' /etc/xray/config.json
systemctl restart xray
echo "DOMAIN=$DOMAIN"
echo "NTLS=$NTLS"
echo "EXP={exp_date}"
"""
        rc, out, err = await self._ssh(host, remote, ssh_user, ssh_port, ssh_key_path)
        if rc != 0:
            raise RuntimeError(f"SSH provision failed rc={rc} OUT={out} ERR={err}")

        dom = re.search(r"DOMAIN=(.*)", out)
        ntls = re.search(r"NTLS=(.*)", out)
        exp = re.search(r"EXP=(.*)", out)

        domain = (dom.group(1).strip() if dom else host)
        port = (ntls.group(1).strip() if ntls else "80")
        exp_date = (exp.group(1).strip() if exp else exp_date)

        link = f"vless://{uuid}@{domain}:{port}?path=/vless&encryption=none&type=ws#{username}"
        return {"domain": domain, "port": port, "exp_date": exp_date, "link": link}
