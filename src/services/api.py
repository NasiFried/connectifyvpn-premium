import asyncio
from fastapi import FastAPI, Request
import uvicorn

class APIService:
    def __init__(self, settings, db):
        self.settings=settings
        self.db=db
        self.app = FastAPI()
        self._server=None
        self._task=None

        @self.app.post("/toyyibpay/callback")
        async def toyyibpay_callback(req: Request):
            # In this template, Telegram bot handles manual verification.
            # You can extend this endpoint to auto-mark orders as paid.
            return {"ok": True}

        @self.app.get("/health")
        async def health():
            return {"ok": True}

    async def initialize(self): return

    async def start(self):
        config = uvicorn.Config(self.app, host=self.settings.server.host, port=self.settings.server.port,
                                log_level=self.settings.server.log_level.lower())
        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._server.serve())
        return

    async def stop(self):
        if self._server:
            self._server.should_exit = True
        if self._task:
            await asyncio.sleep(0.1)
