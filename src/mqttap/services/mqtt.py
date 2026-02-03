import asyncio
import sys
import threading

from aiomqtt import Client, MqttError

from mqttap.config import settings
from mqttap.db.core import create_engine_from_settings
from mqttap.services.storage import store_message

class MqttConsumer:
    def __init__(self) -> None:
        self._client: Client | None = None
        self._task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._engine = None

    async def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._thread_main, daemon=True)
        self._thread.start()

    async def stop(self) -> None:
        if self._loop and self._stop_event:
            asyncio.run_coroutine_threadsafe(self._set_stop(), self._loop)
        if self._thread:
            self._thread.join(timeout=5)

    async def _set_stop(self) -> None:
        if self._stop_event:
            self._stop_event.set()

    def _thread_main(self) -> None:
        if sys.platform == "win32":
            loop = asyncio.SelectorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._stop_event = asyncio.Event()
        self._task = loop.create_task(self._run())
        try:
            self._engine = create_engine_from_settings()
            loop.run_until_complete(self._task)
        finally:
            if self._engine:
                loop.run_until_complete(self._engine.dispose())
            loop.stop()
            loop.close()

    async def _run(self) -> None:
        topics_raw = settings.mqtt_topics
        if isinstance(topics_raw, (list, tuple)):
            topics = [str(t).strip() for t in topics_raw if str(t).strip()]
        else:
            topics = [t.strip() for t in str(topics_raw).split(",") if t.strip()]
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                async with Client(
                    settings.mqtt_host,
                    settings.mqtt_port,
                    username=settings.mqtt_username,
                    password=settings.mqtt_password,
                ) as client:
                    self._client = client
                    for topic in topics:
                        await client.subscribe(topic)
                    async for message in client.messages:
                        await self.handle_message(message.topic, message.payload)
            except MqttError:
                await asyncio.sleep(1)

    async def handle_message(self, topic: str, payload: bytes) -> None:
        if not self._engine:
            return
        await store_message(self._engine, topic, payload)
