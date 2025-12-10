# Chapter 5: Taproot - The Evolution of Bitcoin's Script System

This directory contains the code examples from Chapter 5 of "Mastering Taproot".

## Setup

### Option 1: Using Virtual Environment (Recommended)

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or: venv\Scripts\activate  # On Windows
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Option 2: System-wide Installation

If you prefer to install system-wide (may require `--break-system-packages` flag on newer Python versions):

```bash
pip3 install -r requirements.txt
```

## Code Examples

### 01_demonstrate_key_tweaking.py

Demonstrates the complete key tweaking process that enables Taproot:
- Internal key generation
- Script commitment (empty for key-path-only spending)
- Tweak calculation using BIP341 formula: `t = HashTapTweak(xonly_internal_key || merkle_root)`
- Tweaking application: `P' = P + t×G` and `d' = d + t`
- Mathematical verification of the relationship

**Run:**
```bash
# Make sure virtual environment is activated first
python3 01_demonstrate_key_tweaking.py
```

**Reference:** Chapter 5, Section "Key Tweaking: The Bridge to Taproot" (lines 178-249)

**Key Concepts:**
- Internal key vs output key
- Tweak calculation (BIP341 HashTapTweak)
- Key tweaking formula
- Dual spending paths (key path vs script path)
- Cryptographic binding
- Privacy through indistinguishability

**Expected Output:**
- Step 1: Internal key generation (private and public keys)
- Step 2: Script commitment (empty for key-path-only)
- Step 3: Tweak calculation with preimage and hash
- Step 4: Tweaking application showing key transformation
- Step 5: Mathematical verification
- Key insights about dual spending paths and privacy

### 02_create_simple_taproot_transaction.py

Demonstrates creating a basic Taproot-to-Taproot transaction:
- Taproot address generation (automatic tweaking)
- Transaction construction with SegWit enabled
- Schnorr signature creation (64-byte fixed size)
- Minimal witness structure (only signature, no public key)
- Transaction size and efficiency analysis

**Run:**
```bash
# Make sure virtual environment is activated first
python3 02_create_simple_taproot_transaction.py
```

**Reference:** Chapter 5, Section "Simple Taproot Transaction: Putting It All Together" (lines 283-367)

**Key Concepts:**
- Taproot address generation
- Schnorr signature (64-byte fixed size)
- Minimal witness (only signature needed)
- Transaction efficiency comparison
- Identical appearance of simple and complex transactions

**Transaction Details:**
- **From Address:** Generated from private key (P2TR, Taproot address)
- **To Address:** `tb1p53ncq9ytax924ps66z6al3wfhy6a29w8h6xfu27xem06t98zkmvsakd43h` (P2TR)
- **Input Amount:** 0.00029200 BTC
- **Send Amount:** 0.00029000 BTC
- **Fee:** 0.00000200 BTC
- **UTXO TXID:** `b0f49d2f30f80678c6053af09f0611420aacf20105598330cb3f0ccb8ac7d7f0` (example)
- **UTXO VOUT:** 0

**Expected Output:**
- Transaction setup with Taproot addresses
- Unsigned transaction hex and TXID
- Signed transaction with Schnorr signature
- Transaction size and virtual size
- Efficiency comparison with Legacy and SegWit
- Key observations about Taproot's advantages

## Key Concepts Covered

### Schnorr Signatures
- **Linearity Property:** Enables key aggregation and single-signature output
- **Fixed Size:** Exactly 64 bytes (32 + 32 for r and s values)
- **Non-malleable:** Deterministic nonces and strict encoding rules
- **Efficient Verification:** Faster and simpler than ECDSA

### Key Tweaking (Tweakable Commitment)
- **Formula:** `P' = P + t×G` where `t = HashTapTweak(xonly_internal_key || merkle_root)`
- **Private Key:** `d' = d + t (mod n)`
- **Dual Paths:** Key path (cooperative) and script path (fallback)
- **Cryptographic Binding:** Output key commits to script conditions

### Taproot Architecture
- **Witness Version 1:** `OP_1 <32-byte-output-key>` in scriptPubKey
- **Minimal Witness:** Only signature needed (no public key)
- **Pattern Recognition:** Bitcoin Core detects `OP_1 <32-bytes>` as Taproot
- **Stack Execution:** Schnorr signature verification against output key

### Privacy and Efficiency
- **Uniform Appearance:** Simple and complex transactions look identical
- **Size Efficiency:** ~135 bytes (vs ~165 for SegWit, ~225 for Legacy)
- **Information Hiding:** No revelation of internal complexity until spent
- **Cooperative Incentives:** Smaller fees and better privacy for cooperation

### Programming Differences from SegWit
- **Address Generation:** Must get public key first, then Taproot address
- **Signing Method:** `sign_taproot_input()` uses Schnorr signatures
- **Witness Structure:** Only signature needed, no public key
- **Script Format:** Uses arrays for scripts and amounts

## Dependencies

- `bitcoin-utils>=0.7.0`: Bitcoin transaction and script utilities
- `base58>=2.0.0`: Base58 encoding/decoding

## Notes

- All examples use **testnet** for safety
- Transaction IDs and addresses are examples for demonstration
- Real transactions require valid UTXOs and proper fee calculation
- Key tweaking demonstrates the mathematical foundation for Taproot
- The simple transaction example shows key-path spending (cooperative)
- Script-path spending (with Merkle trees) is covered in later chapters

## Related Chapters

- **Chapter 4:** SegWit foundation (witness structure, malleability resistance)
- **Chapter 6:** Building real Taproot contracts with script paths
- **Chapter 7:** Dual-leaf script tree implementation
- **Chapter 8:** Four-leaf script tree for enterprise-grade contracts

