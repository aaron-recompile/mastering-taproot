# Chapter 3: P2SH Script Engineering - From Multi-signature to Time Locks

This directory contains the code examples from Chapter 3 of "Mastering Taproot".

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

### 01_create_multisig_p2sh.py

Demonstrates how to create a 2-of-3 multi-signature P2SH address:
- Constructing a multi-signature redeem script using OP_CHECKMULTISIG
- Generating a P2SH address from the redeem script
- Understanding script serialization

**Run:**
```bash
# Make sure virtual environment is activated first
python3 01_create_multisig_p2sh.py
```

**Reference:** Chapter 3, Section "3.2 Multi-signature Treasury: 2-of-3 Corporate Security" (lines 62-89)

**Key Concepts:**
- Multi-signature script construction
- P2SH address generation from redeem scripts
- Script serialization and hash computation

---

### 02_spend_multisig_p2sh.py

Demonstrates how to spend a multi-signature P2SH UTXO:
- Creating a transaction with P2SH input
- Signing with multiple private keys (2-of-3)
- Constructing ScriptSig with signatures and redeem script

**Run:**
```bash
python3 02_spend_multisig_p2sh.py
```

**Reference:** Chapter 3, Section "3.2 Multi-signature Treasury: 2-of-3 Corporate Security" (lines 119-142)

**Key Concepts:**
- Multi-signature transaction signing
- ScriptSig construction for P2SH
- OP_CHECKMULTISIG bug workaround (OP_0)

**Transaction Details:**
- Network: Bitcoin Testnet
- Input UTXO TXID: `4b869865bc4a156d7e0ba14590b5c8971e57b8198af64d88872558ca88a8ba5f`
- Output Transaction ID: `e68bef534c7536300c3ae5ccd0f79e031cab29d262380a37269151e8ba0fd4e0` (example from book)

---

### 03_create_csv_script.py

Demonstrates how to create a CSV time-locked P2SH script:
- Creating a relative time lock (3 blocks)
- Combining CSV with P2PKH signature verification
- Generating a P2SH address from the time-locked script

**Run:**
```bash
python3 03_create_csv_script.py
```

**Reference:** Chapter 3, Section "3.3 Time-Locked Inheritance: CSV-Enhanced P2SH" (lines 320-345)

**Key Concepts:**
- CheckSequenceVerify (CSV) relative time locks
- Combining time locks with signature verification
- Sequence value encoding

---

### 04_spend_csv_script.py

Demonstrates how to spend a CSV time-locked P2SH UTXO:
- Setting the sequence number in the transaction input
- Understanding the time lock requirement
- Providing signature and redeem script

**Run:**
```bash
python3 04_spend_csv_script.py
```

**Reference:** Chapter 3, Section "3.3 Time-Locked Inheritance: CSV-Enhanced P2SH" (lines 357-372)

**Key Concepts:**
- Transaction input sequence numbers
- CSV time lock enforcement
- Time-locked transaction spending

**Transaction Details:**
- Network: Bitcoin Testnet
- Transaction ID: `34f5bf0cf328d77059b5674e71442ded8cdcfc723d0136733e0dbf180861906f`
- Time Lock: 3 blocks

**Important Note:**
This transaction will only be accepted by the network if at least 3 blocks have passed since the UTXO was created. Attempting to spend before the time lock expires will result in a "non-BIP68-final" error.

---

## Running All Examples

To run all examples at once (make sure virtual environment is activated):

```bash
source venv/bin/activate  # Activate virtual environment first
python3 01_create_multisig_p2sh.py
python3 02_spend_multisig_p2sh.py
python3 03_create_csv_script.py
python3 04_spend_csv_script.py
```

## Notes

- All examples use the `bitcoin-utils` library for Bitcoin transaction operations
- The examples use testnet for safe experimentation
- Multi-signature examples demonstrate 2-of-3 authorization patterns
- CSV examples demonstrate relative time locks (block-based delays)
- Understanding P2SH is crucial for learning Taproot's script tree structures

## Understanding P2SH

### Two-Stage Verification

P2SH operates through two distinct phases:

1. **Hash Verification**: Verify that the provided redeem script hashes to the expected value
2. **Script Execution**: Execute the redeem script with the provided data

### Multi-signature Scripts

Multi-signature scripts use `OP_CHECKMULTISIG` to require multiple signatures:
- Format: `OP_M <pubkey1> ... <pubkeyN> OP_N OP_CHECKMULTISIG`
- Requires M signatures from N public keys
- Note: Requires `OP_0` before signatures due to a known bug

### CSV Time Locks

CheckSequenceVerify (CSV) enables relative time locks:
- Format: `<delay> OP_CHECKSEQUENCEVERIFY OP_DROP <script>`
- Enforces that `nSequence >= delay` blocks have passed
- Commonly combined with P2PKH for time-locked inheritance

### P2SH vs Taproot

While P2SH enables complex scripts, it has limitations:
- Full redeem script must be revealed during spending
- No selective disclosure of script branches
- Higher transaction fees due to script size

Taproot addresses these limitations by allowing scripts to remain hidden until needed and using Merkle trees for selective disclosure.

