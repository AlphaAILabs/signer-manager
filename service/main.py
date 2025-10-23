from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict
import ctypes
import platform
import os
import json
import logging
import asyncio
from collections import defaultdict
from eth_account import Account
from eth_account.messages import encode_defunct
from starlette.middleware.base import BaseHTTPMiddleware

# Import nonce manager
from service.nonce_manager import nonce_manager

logging.basicConfig(level=logging.DEBUG)

app = FastAPI(
    title="Lighter Signing Service (Thread-Safe with Global Lock)",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# Custom CORS middleware to ensure headers are added
class CustomCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            response.status_code = 200
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "3600"
            return response

        # Process regular requests
        response = await call_next(request)

        # Add CORS headers to response
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"

        return response


# Add custom CORS middleware
app.add_middleware(CustomCORSMiddleware)


@app.on_event("startup")
async def startup_event():
    """Check if signer is initialized on startup"""
    logging.info("=" * 60)
    logging.info("Service starting up...")
    logging.info(f"CORS middleware enabled: allow_origins=['*'], allow_methods=['*']")
    logging.info("=" * 60)
    if signer is None:
        logging.error("=" * 60)
        logging.error("CRITICAL: Signer failed to initialize!")
        logging.error(f"Platform: {platform.system()}/{platform.machine()}")
        logging.error("The service will start but signing operations will fail.")
        logging.error("=" * 60)
    else:
        logging.info(f"Signer initialized successfully on {platform.system()}/{platform.machine()}")


class ApiKeyResponse(ctypes.Structure):
    _fields_ = [("privateKey", ctypes.c_char_p), ("publicKey", ctypes.c_char_p), ("err", ctypes.c_char_p)]


class StrOrErr(ctypes.Structure):
    _fields_ = [("str", ctypes.c_char_p), ("err", ctypes.c_char_p)]


def _initialize_signer():
    is_linux = platform.system() == "Linux"
    is_mac = platform.system() == "Darwin"
    is_windows = platform.system() == "Windows"
    is_x64 = platform.machine().lower() in ("amd64", "x86_64")
    is_arm = platform.machine().lower() == "arm64"

    current_file_directory = os.path.dirname(os.path.abspath(__file__))
    path_to_signer_folders = os.path.join(current_file_directory, "signers")

    if is_arm and is_mac:
        logging.debug("Detected ARM architecture on macOS.")
        return ctypes.CDLL(os.path.join(path_to_signer_folders, "signer-arm64.dylib"))
    elif is_linux and is_x64:
        logging.debug("Detected x64/amd architecture on Linux.")
        return ctypes.CDLL(os.path.join(path_to_signer_folders, "signer-amd64.so"))
    elif is_windows and is_x64:
        logging.debug("Detected x64/amd architecture on Windows.")
        return ctypes.CDLL(os.path.join(path_to_signer_folders, "signer-amd64.dll"))
    else:
        raise Exception(
            f"Unsupported platform/architecture: {platform.system()}/{platform.machine()}. "
            "Currently supported: Linux(x86_64), macOS(arm64), and Windows(x86_64)."
        )


try:
    signer = _initialize_signer()
except Exception as e:
    logging.error(f"Failed to initialize signer: {e}")
    signer = None

# Store client configurations and private keys
clients = {}
api_key_dict = {}  # Store api_key_index -> private_key mapping

# Global lock to ensure thread safety
# CRITICAL: The underlying Go library (sharedlib.go) uses unprotected global state:
#   - var txClient *Client (current active client)
#   - var backupTxClients map[uint8]*Client (client storage)
# SwitchAPIKey() modifies txClient without synchronization, creating race conditions.
# This global lock ensures that switch + sign operations are atomic across ALL accounts.
# Trade-off: Sacrifices concurrency for correctness - all signing operations are serialized.
global_signer_lock = asyncio.Lock()


class CreateClientRequest(BaseModel):
    url: str
    private_key: str
    chain_id: Optional[int] = None
    api_key_index: int
    account_index: int


class CreateApiKeyRequest(BaseModel):
    seed: str = ""


class SignChangeApiKeyRequest(BaseModel):
    api_key_index: int
    account_index: int
    eth_private_key: str
    new_pubkey: str
    nonce: int = -1


class SignCreateOrderRequest(BaseModel):
    api_key_index: int
    account_index: int
    market_index: int
    client_order_index: int
    base_amount: int
    price: int
    is_ask: int
    order_type: int
    time_in_force: int
    reduce_only: int = 0
    trigger_price: int = 0
    order_expiry: int = -1
    nonce: int = -1


class SignCancelOrderRequest(BaseModel):
    api_key_index: int
    account_index: int
    market_index: int
    order_index: int
    nonce: int = -1


class SignWithdrawRequest(BaseModel):
    api_key_index: int
    account_index: int
    usdc_amount: int
    nonce: int = -1


class SignCreateSubAccountRequest(BaseModel):
    api_key_index: int
    account_index: int
    nonce: int = -1


class SignCancelAllOrdersRequest(BaseModel):
    api_key_index: int
    account_index: int
    time_in_force: int
    time: int
    nonce: int = -1


class SignModifyOrderRequest(BaseModel):
    api_key_index: int
    account_index: int
    market_index: int
    order_index: int
    base_amount: int
    price: int
    trigger_price: int
    nonce: int = -1


class SignTransferRequest(BaseModel):
    api_key_index: int
    account_index: int
    eth_private_key: str
    to_account_index: int
    usdc_amount: int
    fee: int
    memo: str
    nonce: int = -1


class SignCreatePublicPoolRequest(BaseModel):
    api_key_index: int
    account_index: int
    operator_fee: int
    initial_total_shares: int
    min_operator_share_rate: int
    nonce: int = -1


class SignUpdatePublicPoolRequest(BaseModel):
    api_key_index: int
    account_index: int
    public_pool_index: int
    status: int
    operator_fee: int
    min_operator_share_rate: int
    nonce: int = -1


class SignMintSharesRequest(BaseModel):
    api_key_index: int
    account_index: int
    public_pool_index: int
    share_amount: int
    nonce: int = -1


class SignBurnSharesRequest(BaseModel):
    api_key_index: int
    account_index: int
    public_pool_index: int
    share_amount: int
    nonce: int = -1


class SignUpdateLeverageRequest(BaseModel):
    api_key_index: int
    account_index: int
    market_index: int
    fraction: int
    margin_mode: int
    nonce: int = -1


class CreateAuthTokenRequest(BaseModel):
    api_key_index: int
    account_index: int
    deadline: int


class SwitchApiKeyRequest(BaseModel):
    api_key_index: int


class CheckClientRequest(BaseModel):
    api_key_index: int
    account_index: int


def get_client_key(api_key_index: int, account_index: int) -> str:
    return f"{api_key_index}:{account_index}"


async def _switch_api_key_internal(api_key_index: int):
    """Internal function to switch API key - must be called within a lock"""
    if not signer:
        raise HTTPException(status_code=500, detail="Signer not initialized")

    signer.SwitchAPIKey.argtypes = [ctypes.c_int]
    signer.SwitchAPIKey.restype = ctypes.c_char_p

    result = signer.SwitchAPIKey(api_key_index)
    if result:
        error_msg = result.decode("utf-8")
        raise HTTPException(status_code=400, detail=f"Failed to switch API key: {error_msg}")


@app.get("/health")
async def health_check():
    """Simple health check endpoint to test CORS"""
    return {
        "status": "ok",
        "service": "Lighter Signing Service",
        "version": "3.0.0",
        "signer_initialized": signer is not None
    }


@app.post("/create_client")
async def create_client(request: CreateClientRequest):
    """
    Create a new client. This operation is thread-safe.
    Uses global lock to prevent race conditions in the underlying Go library.
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        chain_id = request.chain_id
        if chain_id is None:
            chain_id = 304 if "mainnet" in request.url else 300

        private_key = request.private_key
        if private_key.startswith("0x"):
            private_key = private_key[2:]

        # Acquire global lock to ensure thread-safe client creation
        async with global_signer_lock:
            # Store the private key for this api_key_index
            api_key_dict[request.api_key_index] = private_key

            signer.CreateClient.argtypes = [
                ctypes.c_char_p,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_longlong,
            ]
            signer.CreateClient.restype = ctypes.c_char_p

            err = signer.CreateClient(
                request.url.encode("utf-8"),
                private_key.encode("utf-8"),
                chain_id,
                request.api_key_index,
                request.account_index,
            )

            if err:
                err_str = err.decode("utf-8")
                raise HTTPException(status_code=400, detail=err_str)

            client_key = get_client_key(request.api_key_index, request.account_index)
            clients[client_key] = {
                "url": request.url,
                "chain_id": chain_id,
                "api_key_index": request.api_key_index,
                "account_index": request.account_index
            }

            # Initialize nonce for this account/api_key
            try:
                await nonce_manager.initialize_account(
                    account_index=request.account_index,
                    api_key_index=request.api_key_index,
                    api_url=request.url
                )
            except Exception as e:
                logger.warning(f"Could not initialize nonce from API: {e}, will use auto-increment from 0")

        return {"message": "Client created successfully", "client_key": client_key}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in create_client: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/check_client")
async def check_client(request: CheckClientRequest):
    """
    Check if a client exists and is valid. Thread-safe read operation.
    """
    try:
        # Acquire global lock
        async with global_signer_lock:
            signer.CheckClient.argtypes = [
                ctypes.c_int,
                ctypes.c_longlong,
            ]
            signer.CheckClient.restype = ctypes.c_char_p

            result = signer.CheckClient(request.api_key_index, request.account_index)
            if result:
                return {"error": result.decode("utf-8")}
            return {"message": "Client is valid"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/switch_api_key")
async def switch_api_key(request: SwitchApiKeyRequest):
    """
    Switch the active API key. Thread-safe with global locking.
    """
    try:
        async with global_signer_lock:
            await _switch_api_key_internal(request.api_key_index)
            return {"message": "API key switched successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in switch_api_key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create_api_key")
async def create_api_key(request: CreateApiKeyRequest):
    """
    Generate a new API key pair. This operation uses a temporary signer if needed.
    Thread-safe as it doesn't modify global state.
    """
    try:
        if not signer:
            # Create a temporary signer for this operation
            temp_signer = _initialize_signer()
        else:
            temp_signer = signer

        temp_signer.GenerateAPIKey.argtypes = [ctypes.c_char_p]
        temp_signer.GenerateAPIKey.restype = ApiKeyResponse

        result = temp_signer.GenerateAPIKey(ctypes.c_char_p(request.seed.encode("utf-8")))

        private_key_str = result.privateKey.decode("utf-8") if result.privateKey else None
        public_key_str = result.publicKey.decode("utf-8") if result.publicKey else None
        error = result.err.decode("utf-8") if result.err else None

        if error:
            raise HTTPException(status_code=400, detail=error)

        return {
            "private_key": private_key_str,
            "public_key": public_key_str
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in create_api_key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_change_api_key")
async def sign_change_api_key(request: SignChangeApiKeyRequest):
    """
    Sign a change API key transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignChangePubKey.argtypes = [
                    ctypes.c_char_p,
                    ctypes.c_longlong,
                ]
                signer.SignChangePubKey.restype = StrOrErr
                result = signer.SignChangePubKey(ctypes.c_char_p(request.new_pubkey.encode("utf-8")), managed_nonce)

                tx_info_str = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

                tx_info = json.loads(tx_info_str)
                msg_to_sign = tx_info["MessageToSign"]
                del tx_info["MessageToSign"]

                acct = Account.from_key(request.eth_private_key)
                message = encode_defunct(text=msg_to_sign)
                signature = acct.sign_message(message)
                tx_info["L1Sig"] = signature.signature.to_0x_hex()

            return {"tx_info": json.dumps(tx_info)}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_change_api_key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_create_order")
async def sign_create_order(request: SignCreateOrderRequest):
    """
    Sign a create order transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    Different accounts can process requests concurrently without blocking each other.
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        # This ensures requests for the same (account_index, api_key_index) are serialized
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            logging.debug(f"sign_create_order request: api_key_index={request.api_key_index}, "
                         f"market_index={request.market_index}, "
                         f"client_order_index={request.client_order_index}, base_amount={request.base_amount}, "
                         f"price={request.price}, is_ask={request.is_ask}, "
                         f"order_type={request.order_type}, time_in_force={request.time_in_force}, "
                         f"reduce_only={request.reduce_only}, "
                         f"trigger_price={request.trigger_price}, order_expiry={request.order_expiry}, "
                         f"nonce={request.nonce} → managed_nonce={managed_nonce}")

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignCreateOrder.argtypes = [
                    ctypes.c_int,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                ]
                signer.SignCreateOrder.restype = StrOrErr

                result = signer.SignCreateOrder(
                    request.market_index,
                    request.client_order_index,
                    request.base_amount,
                    request.price,
                    int(request.is_ask),
                    request.order_type,
                    request.time_in_force,
                    request.reduce_only,
                    request.trigger_price,
                    request.order_expiry,
                    managed_nonce,  # Use managed nonce
                )

                tx_info = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

            # Success - nonce manager already incremented
            return {"tx_info": tx_info}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_create_order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_cancel_order")
async def sign_cancel_order(request: SignCancelOrderRequest):
    """
    Sign a cancel order transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignCancelOrder.argtypes = [
                    ctypes.c_int,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                ]
                signer.SignCancelOrder.restype = StrOrErr

                result = signer.SignCancelOrder(request.market_index, request.order_index, managed_nonce)

                tx_info = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

            return {"tx_info": tx_info}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_cancel_order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_withdraw")
async def sign_withdraw(request: SignWithdrawRequest):
    """
    Sign a withdraw transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignWithdraw.argtypes = [ctypes.c_longlong, ctypes.c_longlong]
                signer.SignWithdraw.restype = StrOrErr

                result = signer.SignWithdraw(request.usdc_amount, managed_nonce)

                tx_info = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

            return {"tx_info": tx_info}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_withdraw: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_create_sub_account")
async def sign_create_sub_account(request: SignCreateSubAccountRequest):
    """
    Sign a create sub-account transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignCreateSubAccount.argtypes = [ctypes.c_longlong]
                signer.SignCreateSubAccount.restype = StrOrErr

                result = signer.SignCreateSubAccount(managed_nonce)

                tx_info = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

            return {"tx_info": tx_info}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_create_sub_account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_cancel_all_orders")
async def sign_cancel_all_orders(request: SignCancelAllOrdersRequest):
    """
    Sign a cancel all orders transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignCancelAllOrders.argtypes = [
                    ctypes.c_int,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                ]
                signer.SignCancelAllOrders.restype = StrOrErr

                result = signer.SignCancelAllOrders(request.time_in_force, request.time, managed_nonce)

                tx_info = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

            return {"tx_info": tx_info}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_cancel_all_orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_modify_order")
async def sign_modify_order(request: SignModifyOrderRequest):
    """
    Sign a modify order transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignModifyOrder.argtypes = [
                    ctypes.c_int,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                ]
                signer.SignModifyOrder.restype = StrOrErr

                result = signer.SignModifyOrder(
                    request.market_index,
                    request.order_index,
                    request.base_amount,
                    request.price,
                    request.trigger_price,
                    managed_nonce
                )

                tx_info = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

            return {"tx_info": tx_info}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_modify_order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_transfer")
async def sign_transfer(request: SignTransferRequest):
    """
    Sign a transfer transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignTransfer.argtypes = [
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                    ctypes.c_char_p,
                    ctypes.c_longlong,
                ]
                signer.SignTransfer.restype = StrOrErr

                result = signer.SignTransfer(
                    request.to_account_index,
                    request.usdc_amount,
                    request.fee,
                    ctypes.c_char_p(request.memo.encode("utf-8")),
                    managed_nonce
                )

                tx_info_str = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

                tx_info = json.loads(tx_info_str)
                msg_to_sign = tx_info["MessageToSign"]
                del tx_info["MessageToSign"]

                acct = Account.from_key(request.eth_private_key)
                message = encode_defunct(text=msg_to_sign)
                signature = acct.sign_message(message)
                tx_info["L1Sig"] = signature.signature.to_0x_hex()

            return {"tx_info": json.dumps(tx_info)}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_transfer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_create_public_pool")
async def sign_create_public_pool(request: SignCreatePublicPoolRequest):
    """
    Sign a create public pool transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignCreatePublicPool.argtypes = [
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                ]
                signer.SignCreatePublicPool.restype = StrOrErr

                result = signer.SignCreatePublicPool(
                    request.operator_fee,
                    request.initial_total_shares,
                    request.min_operator_share_rate,
                    managed_nonce
                )

                tx_info = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

            return {"tx_info": tx_info}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_create_public_pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_update_public_pool")
async def sign_update_public_pool(request: SignUpdatePublicPoolRequest):
    """
    Sign an update public pool transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignUpdatePublicPool.argtypes = [
                    ctypes.c_longlong,
                    ctypes.c_int,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                ]
                signer.SignUpdatePublicPool.restype = StrOrErr

                result = signer.SignUpdatePublicPool(
                    request.public_pool_index,
                    request.status,
                    request.operator_fee,
                    request.min_operator_share_rate,
                    managed_nonce
                )

                tx_info = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

            return {"tx_info": tx_info}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_update_public_pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_mint_shares")
async def sign_mint_shares(request: SignMintSharesRequest):
    """
    Sign a mint shares transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignMintShares.argtypes = [
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                ]
                signer.SignMintShares.restype = StrOrErr

                result = signer.SignMintShares(
                    request.public_pool_index,
                    request.share_amount,
                    managed_nonce
                )

                tx_info = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

            return {"tx_info": tx_info}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_mint_shares: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_burn_shares")
async def sign_burn_shares(request: SignBurnSharesRequest):
    """
    Sign a burn shares transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignBurnShares.argtypes = [
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                    ctypes.c_longlong,
                ]
                signer.SignBurnShares.restype = StrOrErr

                result = signer.SignBurnShares(
                    request.public_pool_index,
                    request.share_amount,
                    managed_nonce
                )

                tx_info = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

            return {"tx_info": tx_info}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_burn_shares: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sign_update_leverage")
async def sign_update_leverage(request: SignUpdateLeverageRequest):
    """
    Sign an update leverage transaction with per-account locking to prevent nonce conflicts.
    Uses account-specific locks to serialize requests for the same (account_index, api_key_index).
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Get API URL from client config for nonce initialization
        client_key = get_client_key(request.api_key_index, request.account_index)
        client_config = clients.get(client_key)
        api_url = client_config.get("url") if client_config else None

        # Get account-specific lock to prevent nonce race conditions
        account_lock = nonce_manager.get_account_lock(request.account_index, request.api_key_index)

        # Hold account lock for the entire nonce get->sign->error handling flow
        async with account_lock:
            # Get managed nonce (auto-increment if request.nonce == -1)
            managed_nonce = await nonce_manager.get_next_nonce(
                account_index=request.account_index,
                api_key_index=request.api_key_index,
                provided_nonce=request.nonce,
                api_url=api_url
            )

            # Acquire global lock to ensure atomic switch + sign (protects C library calls)
            async with global_signer_lock:
                await _switch_api_key_internal(request.api_key_index)

                signer.SignUpdateLeverage.argtypes = [
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_longlong,
                ]
                signer.SignUpdateLeverage.restype = StrOrErr

                result = signer.SignUpdateLeverage(
                    request.market_index,
                    request.fraction,
                    request.margin_mode,
                    managed_nonce
                )

                tx_info = result.str.decode("utf-8") if result.str else None
                error = result.err.decode("utf-8") if result.err else None

                if error:

                    raise HTTPException(status_code=400, detail=error)

            return {"tx_info": tx_info}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sign_update_leverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create_auth_token")
async def create_auth_token(request: CreateAuthTokenRequest):
    """
    Create an authentication token. Thread-safe with global locking.
    """
    try:
        if not signer:
            raise HTTPException(status_code=500, detail="Signer not initialized")

        # Acquire global lock to ensure atomic switch + create
        async with global_signer_lock:
            await _switch_api_key_internal(request.api_key_index)

            signer.CreateAuthToken.argtypes = [ctypes.c_longlong]
            signer.CreateAuthToken.restype = StrOrErr

            result = signer.CreateAuthToken(request.deadline)

            auth = result.str.decode("utf-8") if result.str else None
            error = result.err.decode("utf-8") if result.err else None

            if error:
                raise HTTPException(status_code=400, detail=error)

        return {"auth_token": auth}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in create_auth_token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    signer_status = "initialized" if signer else "failed"
    return {
        "status": "healthy" if signer else "degraded",
        "version": "3.0.0",
        "thread_safe": True,
        "lock_type": "global",
        "signer": signer_status,
        "platform": f"{platform.system()}/{platform.machine()}",
        "note": "All signing operations are serialized for safety"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
