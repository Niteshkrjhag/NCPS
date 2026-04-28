"""
Kafka Event Pipeline — Event Ingestion and Stream Processing.

Source: docs/context/ncps_architecture.md §3.2–3.3
        docs/context/data_collection_protocol.md §2

Event format:
{
  "event_id": "uuid",
  "type": "VOTE | POST | LOCATION",
  "user_id": "uuid",
  "post_id": "uuid | null",
  "timestamp": "iso8601",
  "payload": { ... }
}
"""

from __future__ import annotations

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

from app.config import config

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# Event Schema
# ──────────────────────────────────────────────────────────

class NCPSEvent:
    """Structured NCPS event."""

    def __init__(
        self,
        event_type: str,
        user_id: str,
        post_id: str | None = None,
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
        timestamp: str | None = None,
    ):
        self.event_id = event_id or str(uuid.uuid4())
        self.event_type = event_type  # VOTE, POST, LOCATION
        self.user_id = user_id
        self.post_id = post_id
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.payload = payload or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "type": self.event_type,
            "user_id": self.user_id,
            "post_id": self.post_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }

    def to_json(self) -> bytes:
        return json.dumps(self.to_dict()).encode("utf-8")

    @classmethod
    def from_json(cls, data: bytes) -> NCPSEvent:
        d = json.loads(data.decode("utf-8"))
        return cls(
            event_id=d.get("event_id"),
            event_type=d["type"],
            user_id=d["user_id"],
            post_id=d.get("post_id"),
            timestamp=d.get("timestamp"),
            payload=d.get("payload", {}),
        )


# ──────────────────────────────────────────────────────────
# Kafka Producer (Event Ingestion Layer)
# ──────────────────────────────────────────────────────────

class EventProducer:
    """Publishes NCPS events to Kafka."""

    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start the Kafka producer."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=config.kafka_bootstrap_servers,
        )
        await self._producer.start()
        logger.info("Kafka producer started")

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def publish(self, event: NCPSEvent) -> None:
        """Publish an event to the events topic."""
        if self._producer is None:
            raise RuntimeError("Producer not started")

        await self._producer.send_and_wait(
            config.kafka_events_topic,
            value=event.to_json(),
            key=event.user_id.encode("utf-8"),
        )
        logger.debug(f"Published event: {event.event_type} for user {event.user_id}")


# ──────────────────────────────────────────────────────────
# Kafka Consumer (Stream Processor)
# ──────────────────────────────────────────────────────────

# Handler type: async function taking an NCPSEvent
EventHandler = Callable[[NCPSEvent], Awaitable[None]]


class EventConsumer:
    """
    Consumes events from Kafka and routes to handlers.
    Source: ncps_architecture.md §3.3

    Processing model:
      for each event e:
          route_to_handler(e.type)
    """

    def __init__(self) -> None:
        self._consumer: AIOKafkaConsumer | None = None
        self._handlers: dict[str, EventHandler] = {}
        self._running = False

    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        self._handlers[event_type] = handler

    async def start(self) -> None:
        """Start the Kafka consumer."""
        self._consumer = AIOKafkaConsumer(
            config.kafka_events_topic,
            bootstrap_servers=config.kafka_bootstrap_servers,
            group_id="ncps-stream-processor",
            auto_offset_reset="latest",
        )
        await self._consumer.start()
        self._running = True
        logger.info("Kafka consumer started")

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")

    async def consume(self) -> None:
        """Main consumption loop — routes events to handlers."""
        if self._consumer is None:
            raise RuntimeError("Consumer not started")

        logger.info("Stream processor consuming events...")
        async for message in self._consumer:
            if not self._running:
                break
            try:
                event = NCPSEvent.from_json(message.value)
                handler = self._handlers.get(event.event_type)
                if handler:
                    await handler(event)
                else:
                    logger.warning(f"No handler for event type: {event.event_type}")
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)


# Singleton instances
producer = EventProducer()
consumer = EventConsumer()
