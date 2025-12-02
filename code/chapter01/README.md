# Chapter 1: Private Keys, Public Keys, and Address Encoding

This directory contains the code examples from Chapter 1 of "Mastering Taproot".

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

### 01_generate_private_key.py
Demonstrates how to generate Bitcoin private keys in hexadecimal and WIF formats.

**Run:**
```bash
# Make sure virtual environment is activated first
python3 01_generate_private_key.py
```

**Reference:** Chapter 1, Section "Generating Private Keys" (lines 24-49)

---

### 02_generate_public_key.py
Shows how to generate compressed and uncompressed public keys.

**Run:**
```bash
python3 02_generate_public_key.py
```

**Reference:** Chapter 1, Section "Compressed vs Uncompressed Public Keys" (lines 124-141)

---

### 03_taproot_xonly_pubkey.py
Demonstrates extraction of x-only public keys for Taproot.

**Run:**
```bash
python3 03_taproot_xonly_pubkey.py
```

**Reference:** Chapter 1, Section "X-Only Public Keys: Taproot's Innovation" (lines 153-158)

---

### 04_generate_addresses.py
Generates all major Bitcoin address types from a single key pair.

**Run:**
```bash
python3 04_generate_addresses.py
```

**Reference:** Chapter 1, Section "Address Generation: From Public Keys to Payment Destinations" (lines 183-206)

---

### 05_verify_addresses.py
Verifies address formats, byte sizes, and explains why Taproot addresses are longer.

**Run:**
```bash
python3 05_verify_addresses.py
```

This script demonstrates:
- Address format validation (Base58Check, Bech32, Bech32m)
- Byte size verification for each address type
- Why Taproot addresses are longer (32-byte x-only pubkeys vs 20-byte hashes)

---

## Running All Examples

To run all examples at once (make sure virtual environment is activated):

```bash
source venv/bin/activate  # Activate virtual environment first
python3 01_generate_private_key.py
python3 02_generate_public_key.py
python3 03_taproot_xonly_pubkey.py
python3 04_generate_addresses.py
python3 05_verify_addresses.py  # Verify address formats and sizes
```

## Notes

- All examples use the `bitcoin-utils` library for Bitcoin key and address operations
- Each script generates a new random key pair when run
- Output values will differ each time you run the scripts (as expected for cryptographic operations)
- The library properly supports Taproot addresses (P2TR) with the `bc1p` prefix

