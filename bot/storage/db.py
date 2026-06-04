"""
Database — Async MongoDB connection via Motor.

Manages the connection lifecycle and provides access
to the SpotNake database collections.
"""

from __future__ import annotations

import logging
from typing import Optional

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

logger = logging.getLogger(__name__)


class Database:
    """Async MongoDB connection manager."""

    def __init__(self):
        self._client: Optional[AsyncMongoClient] = None
        self._db: Optional[AsyncDatabase] = None

    async def connect(self, uri: str, db_name: str) -> None:
        """Establish connection to MongoDB Atlas.
        
        Args:
            uri: MongoDB connection string.
            db_name: Database name to use.
        """
        self._client = AsyncMongoClient(uri)
        self._db = self._client[db_name]
        
        # Verify connection
        try:
            await self._client.admin.command("ping")
            logger.info(f"✅ MongoDB connected: {db_name}")
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise

    async def disconnect(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            await self._client.close()
            logger.info("MongoDB disconnected")

    @property
    def db(self) -> AsyncDatabase:
        """Get the database instance."""
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db

    @property
    def taste_vectors(self):
        """Collection for taste profile embeddings."""
        return self.db["taste_vectors"]

    @property
    def play_history(self):
        """Collection for play/download history."""
        return self.db["play_history"]

    @property
    def user_preferences(self):
        """Collection for user preference metadata."""
        return self.db["user_preferences"]

    async def is_connected(self) -> bool:
        """Check if the database connection is alive."""
        try:
            if self._client:
                await self._client.admin.command("ping")
                return True
        except Exception:
            pass
        return False
