"""
Nonce Manager for Signer Service
Adapted from lighter-python's nonce_manager.py
Manages nonce state to prevent signature conflicts
"""
import asyncio
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


# REMOVED: Signer-manager should NEVER access Lighter API directly
# This would expose signer-manager's IP instead of the client's IP
# Clients should fetch nonce themselves and pass it to signer-manager


class NonceManager:
    """
    Nonce manager for signer service

    Responsibilities:
    - Provide per-account locks to serialize signing requests
    - Prevent concurrent nonce conflicts for same (account_index, api_key_index)

    NOT responsible for:
    - Nonce caching (client provides nonce from Lighter API)
    - Nonce auto-increment (client manages nonce)
    - Nonce rollback (client retries with fresh nonce from API)
    """

    def __init__(self):
        # Per-account locks to serialize requests for the same (account_index, api_key_index)
        self.account_locks: Dict[Tuple[int, int], asyncio.Lock] = {}

    async def initialize_account(self, account_index: int, api_key_index: int, api_url: str):
        """
        No-op: Account initialization not needed

        Client manages nonce by fetching from Lighter API.
        account_lock is created on-demand in get_account_lock().
        """
        pass

    async def get_next_nonce(
        self,
        account_index: int,
        api_key_index: int,
        provided_nonce: int = -1,
        api_url: Optional[str] = None
    ) -> int:
        """
        Get the nonce for signing - ALWAYS use client-provided value

        Args:
            account_index: Account index
            api_key_index: API key index
            provided_nonce: Client-provided nonce from Lighter API (REQUIRED)
            api_url: API URL (for reference only)

        Returns:
            Nonce to use for signing

        Raises:
            ValueError: If client does not provide nonce
        """
        # Client MUST provide nonce from Lighter API
        if provided_nonce < 0:
            raise ValueError(
                f"Client must provide nonce from Lighter API. "
                f"account_index={account_index}, api_key_index={api_key_index}. "
                f"Nonce management is client's responsibility to avoid IP exposure."
            )

        logger.debug(f"Using client-provided nonce: account={account_index}, api_key={api_key_index}, nonce={provided_nonce}")

        # Simply return client's value - no cache, no auto-increment, no interference
        return provided_nonce

    def get_account_lock(self, account_index: int, api_key_index: int) -> asyncio.Lock:
        """
        Get or create a lock for a specific (account_index, api_key_index) pair.
        This lock should be held during the entire signing process to prevent race conditions.

        Args:
            account_index: Account index
            api_key_index: API key index

        Returns:
            Lock for this account/api_key pair
        """
        key = (account_index, api_key_index)
        if key not in self.account_locks:
            self.account_locks[key] = asyncio.Lock()
        return self.account_locks[key]


# Global singleton instance
nonce_manager = NonceManager()
