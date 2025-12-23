import aiohttp

class PaymentService:
    def __init__(self, settings, db):
        self.settings=settings
        self.db=db

    async def initialize(self): return
    async def start(self): return
    async def stop(self): return

    async def create_bill(self, *, amount_sen: int, name: str, desc: str, external_ref: str,
                          return_url: str, callback_url: str) -> str:
        url = f"{self.settings.payment.toyyibpay_base_url.rstrip('/')}/index.php/api/createBill"
        data = {
            "userSecretKey": self.settings.payment.toyyibpay_secret_key,
            "categoryCode": self.settings.payment.toyyibpay_category_code,
            "billName": name[:30],
            "billDescription": desc[:100],
            "billPriceSetting": "1",
            "billPayorInfo": "0",
            "billAmount": str(amount_sen),
            "billReturnUrl": return_url,
            "billCallbackUrl": callback_url,
            "billExternalReferenceNo": external_ref,
            "billPaymentChannel": "2",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, timeout=30) as resp:
                js = await resp.json(content_type=None)
                if resp.status != 200:
                    raise RuntimeError(f"ToyyibPay createBill failed: {resp.status} {js}")
                bill_code = js[0].get("BillCode") if isinstance(js, list) and js else None
                if not bill_code:
                    raise RuntimeError(f"ToyyibPay createBill unexpected: {js}")
                return bill_code

    async def get_transactions(self, bill_code: str):
        url = f"{self.settings.payment.toyyibpay_base_url.rstrip('/')}/index.php/api/getBillTransactions"
        data = {"billCode": bill_code}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, timeout=30) as resp:
                js = await resp.json(content_type=None)
                if resp.status != 200:
                    raise RuntimeError(f"ToyyibPay getBillTransactions failed: {resp.status} {js}")
                return js
