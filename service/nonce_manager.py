"""
Nonce Manager for Signer Service
Adapted from lighter-python's nonce_manager.py
Manages nonce state to prevent signature conflicts
"""
import asyncio
import logging
from typing import Dict, Tuple, Optional
import aiohttp

logger = logging.getLogger(__name__)


# REMOVED: Signer-manager should NEVER access Lighter API directly
# This would expose signer-manager's IP instead of the client's IP
# Clients should fetch nonce themselves and pass it to signer-manager


class OptimisticNonceManager:
    """
    Optimistic nonce manager (similar to lighter-python)

    Features:
    - Tracks nonce per (account_index, api_key_index)
    - Auto-increments nonces
    - Rollback on failure
    - Hard refresh when 'invalid nonce' error occurs
    """

    def __init__(self):
        # Structure: {account_index: {api_key_index: current_nonce}}
        self.nonces: Dict[int, Dict[int, int]] = {}
        self.lock = asyncio.Lock()  # Global lock for internal state updates
        self.api_urls: Dict[int, str] = {}  # account_index -> api_url mapping
        # Per-account locks to serialize requests for the same (account_index, api_key_index)
        self.account_locks: Dict[Tuple[int, int], asyncio.Lock] = {}

    async def initialize_account(self, account_index: int, api_key_index: int, api_url: str):
        """
        Initialize nonce for a new account/api_key pair

        IMPORTANT: Signer-manager starts from 0. Clients MUST fetch the real nonce
        from Lighter API themselves and pass it in signing requests.
        This ensures the client's IP is visible to Lighter, not the signer's IP.

        Args:
            account_index: Account index
            api_key_index: API key index
            api_url: Lighter API URL (stored for reference only)
        """
        async with self.lock:
            # Store API URL for reference only (not used to fetch nonce)
            self.api_urls[account_index] = api_url

            if account_index not in self.nonces:
                self.nonces[account_index] = {}

            if api_key_index not in self.nonces[account_index]:
                # Always start from 0
                # Client is responsible for passing correct nonce from Lighter API
                self.nonces[account_index][api_key_index] = 0
                logger.info(f"Initialized nonce cache: account={account_index}, api_key={api_key_index}, starting from 0")

    async def get_next_nonce(
        self,
        account_index: int,
        api_key_index: int,
        provided_nonce: int = -1,
        api_url: Optional[str] = None
    ) -> int:
        """
        Get the next nonce for signing

        Args:
            account_index: Account index
            api_key_index: API key index
            provided_nonce: Client-provided nonce (-1 means auto-manage)
            api_url: API URL (required for first-time initialization)

        Returns:
            Nonce to use for signing
        """
        async with self.lock:
            # Ensure account is initialized
            if account_index not in self.nonces:
                self.nonces[account_index] = {}

            if api_key_index not in self.nonces[account_index]:
                # Initialize on-the-fly - always start from 0
                # Client must provide real nonce from Lighter API
                if api_url:
                    self.api_urls[account_index] = api_url
                self.nonces[account_index][api_key_index] = 0
                logger.info(f"On-the-fly nonce init: account={account_index}, api_key={api_key_index}, starting from 0")

            # If client provides nonce >= 0, respect it (backward compatibility)
            # But update our cache to avoid going backwards
            if provided_nonce >= 0:
                # Update cache to max(cache, provided)
                current = self.nonces[account_index][api_key_index]
                if provided_nonce > current:
                    self.nonces[account_index][api_key_index] = provided_nonce
                    logger.debug(f"Using client nonce: account={account_index}, api_key={api_key_index}, nonce={provided_nonce}")
                elif provided_nonce < current:
                    logger.warning(f"Client nonce ({provided_nonce}) < cached nonce ({current}), potential conflict!")
                return provided_nonce

            # Auto-increment mode (like lighter-python)
            self.nonces[account_index][api_key_index] += 1
            nonce = self.nonces[account_index][api_key_index]

            logger.debug(f"Auto-incremented nonce: account={account_index}, api_key={api_key_index}, nonce={nonce}")
            return nonce

    async def acknowledge_failure(self, account_index: int, api_key_index: int):
        """
        Rollback nonce after a failed transaction

        Args:
            account_index: Account index
            api_key_index: API key index
        """
        async with self.lock:
            if account_index in self.nonces and api_key_index in self.nonces[account_index]:
                old_nonce = self.nonces[account_index][api_key_index]
                self.nonces[account_index][api_key_index] -= 1
                new_nonce = self.nonces[account_index][api_key_index]
                logger.warning(f"Rolled back nonce: account={account_index}, api_key={api_key_index}, {old_nonce} → {new_nonce}")

    async def hard_refresh_nonce(self, account_index: int, api_key_index: int):
        """
        Handle 'invalid nonce' error by rolling back

        IMPORTANT: Signer-manager does NOT fetch nonce from Lighter API to avoid IP exposure.
        When 'invalid nonce' occurs, client should:
        1. Fetch fresh nonce from Lighter API (using client's own IP)
        2. Retry the signing request with the fresh nonce

        Args:
            account_index: Account index
            api_key_index: API key index
        """
        async with self.lock:
            logger.error(
                f"Invalid nonce error for account={account_index}, api_key={api_key_index}. "
                f"Client should fetch fresh nonce from Lighter API and retry."
            )
            # Rollback the cached nonce so it can be retried
            if account_index in self.nonces and api_key_index in self.nonces[account_index]:
                old_nonce = self.nonces[account_index][api_key_index]
                self.nonces[account_index][api_key_index] = max(0, old_nonce - 1)
                logger.warning(f"Rolled back nonce: account={account_index}, api_key={api_key_index}, {old_nonce} → {self.nonces[account_index][api_key_index]}")

    async def get_current_nonce(self, account_index: int, api_key_index: int) -> int:
        """Get current cached nonce without incrementing"""
        async with self.lock:
            if account_index in self.nonces and api_key_index in self.nonces[account_index]:
                return self.nonces[account_index][api_key_index]
            return -1

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
nonce_manager = OptimisticNonceManager()
