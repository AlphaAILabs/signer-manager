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


async def get_nonce_from_api(api_url: str, account_index: int, api_key_index: int) -> int:
    """
    Fetch the next nonce from Lighter API

    Args:
        api_url: Lighter API base URL
        account_index: Account index
        api_key_index: API key index

    Returns:
        Next nonce value
    """
    url = f"{api_url}/api/v1/nextNonce"
    params = {"account_index": account_index, "api_key_index": api_key_index}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Failed to get nonce (status {resp.status}): {error_text}")
                data = await resp.json()
                nonce = data.get("nonce")
                if nonce is None:
                    raise Exception(f"Invalid API response: {data}")
                logger.debug(f"Fetched nonce from API: account={account_index}, api_key={api_key_index}, nonce={nonce}")
                return int(nonce)
    except asyncio.TimeoutError:
        raise Exception("Timeout fetching nonce from API")
    except Exception as e:
        logger.error(f"Error fetching nonce from API: {e}")
        raise


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

        Args:
            account_index: Account index
            api_key_index: API key index
            api_url: Lighter API URL
        """
        async with self.lock:
            # Store API URL
            self.api_urls[account_index] = api_url

            if account_index not in self.nonces:
                self.nonces[account_index] = {}

            if api_key_index not in self.nonces[account_index]:
                try:
                    # Fetch current nonce from API
                    nonce = await get_nonce_from_api(api_url, account_index, api_key_index)
                    # Start from current - 1 (will be incremented on first use)
                    self.nonces[account_index][api_key_index] = nonce - 1
                    logger.info(f"Initialized nonce: account={account_index}, api_key={api_key_index}, nonce={nonce - 1}")
                except Exception as e:
                    # If API fetch fails, start from 0
                    logger.warning(f"Could not fetch initial nonce from API: {e}, starting from 0")
                    self.nonces[account_index][api_key_index] = 0

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
                # Initialize on-the-fly
                if api_url:
                    self.api_urls[account_index] = api_url
                    try:
                        nonce = await get_nonce_from_api(api_url, account_index, api_key_index)
                        self.nonces[account_index][api_key_index] = nonce - 1
                    except Exception as e:
                        logger.warning(f"Could not fetch nonce from API: {e}, starting from 0")
                        self.nonces[account_index][api_key_index] = 0
                else:
                    # No API URL, start from 0
                    logger.warning(f"No API URL for account={account_index}, starting nonce from 0")
                    self.nonces[account_index][api_key_index] = 0

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
        Force refresh nonce from API (used when 'invalid nonce' error)

        Args:
            account_index: Account index
            api_key_index: API key index
        """
        async with self.lock:
            api_url = self.api_urls.get(account_index)
            if not api_url:
                logger.error(f"Cannot hard refresh: no API URL for account={account_index}")
                return

            try:
                nonce = await get_nonce_from_api(api_url, account_index, api_key_index)
                if account_index not in self.nonces:
                    self.nonces[account_index] = {}
                old_nonce = self.nonces[account_index].get(api_key_index, -1)
                self.nonces[account_index][api_key_index] = nonce - 1
                logger.info(f"Hard refreshed nonce: account={account_index}, api_key={api_key_index}, {old_nonce} → {nonce - 1}")
            except Exception as e:
                logger.error(f"Failed to hard refresh nonce: {e}")

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
