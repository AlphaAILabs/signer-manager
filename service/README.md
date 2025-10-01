# Lighter Signing Service

A FastAPI-based signing service for the Lighter Protocol, providing cryptographic signing capabilities for trading operations, account management, and liquidity pool interactions.

## Overview

This service acts as a secure signing server that interfaces with the Lighter Protocol's Go SDK through native binaries. It provides REST API endpoints for:

- **Trading Operations**: Create, cancel, and modify orders
- **Account Management**: Create clients, manage API keys, create sub-accounts
- **Liquidity Operations**: Manage public pools, mint/burn shares
- **Transfer Operations**: Withdraw funds and transfer between accounts
- **Authentication**: Generate auth tokens for secure API access

## Features

- 🔐 **Secure Key Management**: Manages API keys and Ethereum private keys
- 🌍 **Cross-Platform Support**: Native binaries for Linux (x64), macOS (ARM64), and Windows (x64)
- 🚀 **High Performance**: Built with FastAPI for async request handling
- 🔄 **Multi-Client Support**: Manage multiple trading clients simultaneously
- 📝 **Comprehensive Signing**: Support for all Lighter Protocol transaction types

## Architecture

The service uses ctypes to interface with native Go binaries that handle the cryptographic operations:

```
┌─────────────────┐
│   FastAPI App   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Python ctypes  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Go SDK Binary  │
│  (signer-*.so)  │
└─────────────────┘
```

## Prerequisites

- Python 3.11+ (Python 3.13 supported with pydantic>=2.8.0)
- pip or poetry for dependency management

## Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd lighter-signing-service
```

2. **Create a virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

## Running the Service

### Development Mode

```bash
python main.py
```

The service will start on `http://0.0.0.0:8000`

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the service is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Client Management

#### `POST /create_client`
Create a new trading client instance.

**Request Body**:
```json
{
  "url": "https://api.lighter.xyz",
  "private_key": "0x...",
  "chain_id": 304,
  "api_key_index": 0,
  "account_index": 0
}
```

#### `POST /check_client`
Check if a client exists for given indices.

#### `POST /switch_api_key`
Switch to a different API key context.

### API Key Management

#### `POST /create_api_key`
Generate a new API key pair.

**Request Body**:
```json
{
  "seed": "optional-seed-string"
}
```

**Response**:
```json
{
  "private_key": "...",
  "public_key": "..."
}
```

#### `POST /sign_change_api_key`
Sign a transaction to change the API key.

### Trading Operations

#### `POST /sign_create_order`
Sign an order creation transaction.

**Request Body**:
```json
{
  "api_key_index": 0,
  "account_index": 0,
  "market_index": 0,
  "client_order_index": 1,
  "base_amount": 1000000,
  "price": 50000,
  "is_ask": 0,
  "order_type": 0,
  "time_in_force": 0,
  "reduce_only": 0,
  "trigger_price": 0,
  "order_expiry": -1,
  "nonce": -1
}
```

#### `POST /sign_cancel_order`
Sign an order cancellation.

#### `POST /sign_modify_order`
Sign an order modification.

#### `POST /sign_cancel_all_orders`
Sign a cancel-all-orders transaction.

### Account Operations

#### `POST /sign_create_sub_account`
Sign a sub-account creation transaction.

#### `POST /sign_withdraw`
Sign a withdrawal transaction.

**Request Body**:
```json
{
  "api_key_index": 0,
  "account_index": 0,
  "usdc_amount": 1000000,
  "nonce": -1
}
```

#### `POST /sign_transfer`
Sign a transfer between accounts (requires L1 signature).



### Liquidity Pool Operations

#### `POST /sign_create_public_pool`
Sign a public pool creation transaction.

**Request Body**:
```json
{
  "api_key_index": 0,
  "account_index": 0,
  "operator_fee": 100,
  "initial_total_shares": 1000000,
  "min_operator_share_rate": 50,
  "nonce": -1
}
```

#### `POST /sign_mint_shares`
Sign a share minting transaction.

#### `POST /sign_burn_shares`
Sign a share burning transaction.

#### `POST /sign_update_public_pool`
Sign a public pool update transaction.

### Authentication

#### `POST /create_auth_token`
Create an authentication token for API access.

**Request Body**:
```json
{
  "api_key_index": 0,
  "deadline": 1704067200
}
```

**Response**:
```json
{
  "auth_token": "..."
}
```

#### `GET /health`
Health check endpoint.

**Response**:
```json
{
  "status": "healthy"
}
```

## Configuration

### Chain IDs

The service automatically detects chain IDs based on the URL:
- **Mainnet**: 304 (if "mainnet" in URL)
- **Testnet**: 300 (default)

You can also explicitly specify the `chain_id` in the `/create_client` request.

### Native Binaries

The service automatically selects the appropriate binary based on your platform:

| Platform | Architecture | Binary File |
|----------|-------------|-------------|
| Linux | x64/AMD64 | `signers/signer-amd64.so` |
| macOS | ARM64 (M1/M2) | `signers/signer-arm64.dylib` |
| Windows | x64/AMD64 | `signers/signer-amd64.dll` |

These binaries are compiled from the [Lighter Go SDK](https://github.com/elliottech/lighter-go).

## Usage Example

### Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Create API key
response = requests.post(f"{BASE_URL}/create_api_key", json={
    "seed": ""
})
api_key = response.json()
print(f"API Key: {api_key['public_key']}")

# 2. Create client
response = requests.post(f"{BASE_URL}/create_client", json={
    "url": "https://api-testnet.lighter.xyz",
    "private_key": api_key["private_key"],
    "api_key_index": 0,
    "account_index": 0
})
print(f"Client created: {response.json()}")

# 3. Create an order
response = requests.post(f"{BASE_URL}/sign_create_order", json={
    "api_key_index": 0,
    "account_index": 0,
    "market_index": 0,
    "client_order_index": 1,
    "base_amount": 1000000,
    "price": 50000,
    "is_ask": 0,
    "order_type": 0,
    "time_in_force": 0,
    "reduce_only": 0,
    "trigger_price": 0,
    "order_expiry": -1,
    "nonce": -1
})
tx_info = response.json()
print(f"Order signed: {tx_info}")
```

### JavaScript/TypeScript Example

```typescript
const BASE_URL = "http://localhost:8000";

// Create API key
const apiKeyResponse = await fetch(`${BASE_URL}/create_api_key`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ seed: "" })
});
const apiKey = await apiKeyResponse.json();

// Create client
const clientResponse = await fetch(`${BASE_URL}/create_client`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    url: "https://api-testnet.lighter.xyz",
    private_key: apiKey.private_key,
    api_key_index: 0,
    account_index: 0
  })
});

// Sign order
const orderResponse = await fetch(`${BASE_URL}/sign_create_order`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    api_key_index: 0,
    account_index: 0,
    market_index: 0,
    client_order_index: 1,
    base_amount: 1000000,
    price: 50000,
    is_ask: 0,
    order_type: 0,
    time_in_force: 0
  })
});
const txInfo = await orderResponse.json();
```

## Security Considerations

⚠️ **Important Security Notes**:

1. **Private Key Storage**: This service stores private keys in memory. In production:
   - Use environment variables or secure key management systems (e.g., AWS KMS, HashiCorp Vault)
   - Never commit private keys to version control
   - Consider using hardware security modules (HSMs) for key storage

2. **Network Security**:
   - Run behind a reverse proxy (nginx, Caddy)
   - Use HTTPS/TLS in production
   - Implement rate limiting
   - Restrict CORS origins (currently set to `*`)

3. **Access Control**:
   - Implement authentication/authorization
   - Use API keys or JWT tokens
   - Log all signing operations
   - Monitor for suspicious activity

4. **Environment Isolation**:
   - Run in isolated environments (containers, VMs)
   - Use separate instances for mainnet and testnet
   - Implement proper firewall rules

## Development

### Project Structure

```
lighter-signing-service/
├── main.py              # FastAPI application and endpoints
├── requirements.txt     # Python dependencies
├── signers/            # Native binaries
│   ├── README.md
│   ├── signer-amd64.dll
│   ├── signer-amd64.so
│   └── signer-arm64.dylib
└── venv/               # Virtual environment (gitignored)
```

### Adding New Endpoints

1. Define the request model using Pydantic:
```python
class MyRequest(BaseModel):
    api_key_index: int
    # ... other fields
```

2. Create the endpoint:
```python
@app.post("/my_endpoint")
async def my_endpoint(request: MyRequest):
    # Implementation
    pass
```

3. Configure ctypes for the Go function:
```python
signer.MyGoFunction.argtypes = [ctypes.c_int, ...]
signer.MyGoFunction.restype = StrOrErr
```

### Testing

```bash
# Run the service
python main.py

# In another terminal, test endpoints
curl -X POST http://localhost:8000/health
```

## Troubleshooting

### Signer Not Initialized

**Error**: `Signer not initialized`

**Solution**: Ensure the correct binary exists for your platform in the `signers/` directory.

### Python 3.13 Compatibility

**Error**: `TypeError: ForwardRef._evaluate() missing 1 required keyword-only argument`

**Solution**: Upgrade pydantic to version 2.8.0 or higher:
```bash
pip install "pydantic>=2.8.0"
```

### Binary Loading Issues

**Error**: `Unsupported platform/architecture`

**Solution**: Check that you have the correct binary for your system. See the [Lighter Go SDK](https://github.com/elliottech/lighter-go) to build binaries for your platform.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Related Projects

- [Lighter Go SDK](https://github.com/elliottech/lighter-go) - Source code for the native binaries
- [Lighter Protocol](https://lighter.xyz) - Official Lighter Protocol website

## Support

For issues and questions:
- Open an issue on GitHub
- Contact the Lighter Protocol team
- Check the [official documentation](https://docs.lighter.xyz)

---

**Note**: This is a signing service that handles sensitive cryptographic operations. Always follow security best practices when deploying to production environments.
