# Chapter 2: Bitcoin Script Fundamentals - Stack Operations and P2PKH

This directory contains the code examples from Chapter 2 of "Mastering Taproot".

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

### 01_build_p2pkh_transaction.py

Demonstrates how to build a complete P2PKH transaction from scratch:
- Creating transaction inputs and outputs
- Signing a P2PKH input with a private key
- Constructing the unlocking script (ScriptSig)
- Serializing the final transaction for broadcast

**Run:**
```bash
# Make sure virtual environment is activated first
python3 01_build_p2pkh_transaction.py
```

**Reference:** Chapter 2, Section "2.3 Practical Implementation: Building a P2PKH transaction" (lines 268-328)

**Key Concepts Demonstrated:**
- UTXO model: Referencing previous transaction outputs
- P2PKH script structure: Locking and unlocking scripts
- Transaction signing: ECDSA signature creation
- Script construction: Building ScriptSig from signature and public key

**Transaction Details:**
- Network: Bitcoin Testnet
- Input: Legacy P2PKH address
- Output: SegWit P2WPKH address
- Transaction ID: `bf41b47481a9d1c99af0b62bb36bc864182312f39a3e1e06c8f6304ba8e58355`

---

## Running All Examples

To run all examples at once (make sure virtual environment is activated):

```bash
source venv/bin/activate  # Activate virtual environment first
python3 01_build_p2pkh_transaction.py
```

## Notes

- All examples use the `bitcoin-utils` library for Bitcoin transaction operations
- The example uses testnet for safe experimentation
- The transaction in the example was successfully broadcast to testnet
- You can view the transaction on a testnet explorer using the transaction ID
- Understanding P2PKH is fundamental for learning more advanced script types like Taproot

## Understanding the Code

### Transaction Structure

A Bitcoin transaction consists of:
- **Inputs**: References to previous UTXOs being spent
- **Outputs**: New UTXOs being created with locking scripts
- **Scripts**: Unlocking scripts (ScriptSig) and locking scripts (ScriptPubKey)

### P2PKH Script Execution

The P2PKH script follows this pattern:
1. Push signature and public key to stack
2. Duplicate public key (OP_DUP)
3. Hash the public key (OP_HASH160)
4. Compare with expected hash (OP_EQUALVERIFY)
5. Verify signature (OP_CHECKSIG)

See Chapter 2 for detailed stack execution traces.

