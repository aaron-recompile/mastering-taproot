# Chapter 4: Building SegWit Transactions - From Construction to Stack Execution, and Witness Structure and Malleability Solutions

This directory contains the code examples from Chapter 4 of "Mastering Taproot".

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

### 01_legacy_vs_segwit_comparison.py

Demonstrates the key differences between legacy P2PKH and SegWit P2WPKH transaction signing:
- Legacy: Signature goes in scriptSig (included in TXID)
- SegWit: Signature goes in witness, scriptSig remains empty (witness excluded from TXID)
- Transaction malleability resistance in SegWit

**Run:**
```bash
# Make sure virtual environment is activated first
python3 01_legacy_vs_segwit_comparison.py
```

**Reference:** Chapter 4, Section 4.1 "Legacy vs SegWit Code Comparison" (lines 69-99)

**Key Concepts:**
- Legacy transaction structure and signing
- SegWit transaction structure and signing
- Witness data separation
- Transaction malleability problem and solution

**Expected Output:**
- Legacy P2PKH signing process with scriptSig
- SegWit P2WPKH signing process with witness
- Comparison of key differences

### 02_create_segwit_transaction.py

Demonstrates building a complete SegWit transaction step by step:
- Phase 1: Create unsigned transaction (empty scriptSig, no witness)
- Phase 2: Add SegWit signature (witness data, scriptSig remains empty)
- Transaction structure analysis and comparison

**Run:**
```bash
# Make sure virtual environment is activated first
python3 02_create_segwit_transaction.py
```

**Reference:** Chapter 4, Sections 4.2 and 4.3 "Creating a Complete SegWit Transaction" and "SegWit Transaction Construction and Analysis" (lines 107-235)

**Key Concepts:**
- SegWit transaction setup and key/address creation
- Unsigned transaction structure
- Witness data addition
- Transaction serialization
- Marker and flag in SegWit transactions
- TXID vs wtxid distinction

**Transaction Details:**
- **From Address:** `tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4` (P2WPKH)
- **To Address:** `tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4` (P2WPKH)
- **Amount:** 0.00000666 BTC (666 satoshis)
- **UTXO TXID:** `1454438e6f417d710333fbab118058e2972127bdd790134ab74937fa9dddbc48` (real testnet UTXO)
- **UTXO VOUT:** 0
- **UTXO Amount:** 1,000 sats
- **Fee:** 334 sats

**✅ Verified Transaction:** This code has been successfully tested and broadcast to testnet.
   TXID: `271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6`
   Explorer: https://blockstream.info/testnet/tx/271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6

**Expected Output:**
- Transaction setup with addresses
- Phase 1: Unsigned transaction with empty scriptSig
- Phase 2: Signed transaction with witness data
- Structure comparison before and after signing
- Transaction size analysis

### 03_parse_segwit_transaction.py

Demonstrates how to actually parse a SegWit transaction hex string and extract all components, comparing hardcoded values with actual parsed transaction data:
- Manual transaction hex parsing
- Extracting version, inputs, outputs, witness data
- Comparing hardcoded vs actual parsing results
- Understanding real transaction structure

**Run:**
```bash
# Make sure virtual environment is activated first
python3 03_parse_segwit_transaction.py
```

**Reference:** Chapter 4, Sections 4.2 and 4.3 (complements 02_create_segwit_transaction.py)

**Key Concepts:**
- Manual transaction hex string parsing
- Variable-length integer (varint) parsing
- Little-endian vs big-endian byte order
- SegWit marker and flag detection
- Witness data extraction
- Comparison between expected and actual values

**Expected Output:**
- Phase 1: Parsed unsigned transaction components
- Hardcoded values from 02_create_segwit_transaction.py
- Phase 2: Parsed signed transaction with witness
- Comparison showing differences between hardcoded and actual values
- Explanation of why they differ and what each approach teaches

## Key Concepts Covered

### Transaction Malleability
- The problem: Signature encoding variations change TXID without affecting validity
- The solution: SegWit separates witness data from TXID calculation
- Impact: Enables Lightning Network and Layer 2 protocols

### SegWit Architecture
- **Base Transaction:** Version, inputs, outputs, locktime (used for TXID)
- **Witness Data:** Signatures and scripts (excluded from TXID)
- **Marker and Flag:** `00 01` in serialized form (indicates SegWit, participates in wtxid)

### P2WPKH Structure
- **ScriptPubKey:** `OP_0 <20-byte-pubkey-hash>` (witness version 0)
- **Witness:** `[signature, public_key]` (2 items)
- **ScriptSig:** Empty (`00`)

### Execution Model
- Bitcoin Core recognizes `OP_0 <20-bytes>` as P2WPKH
- Executes equivalent to P2PKH: `OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG`
- Pattern recognition enables witness program execution

### Economic Framework
- **Transaction Weight:** `(Base Size × 4) + Witness Size`
- **Virtual Size:** `Weight ÷ 4`
- Witness bytes charged at 1 weight unit/byte
- Base bytes charged at 4 weight units/byte
- Enables economic viability for complex scripts

## Dependencies

- `bitcoin-utils>=0.7.0`: Bitcoin transaction and script utilities
- `base58>=2.0.0`: Base58 encoding/decoding

## Notes

- All examples use **testnet** for safety
- Transaction IDs and addresses are real testnet examples, provided for reproducible demonstrations.
- Real transactions require valid UTXOs and proper fee calculation
- The witness structure demonstrated here is the foundation for Taproot (Chapter 5+)

## Related Chapters

- **Chapter 2:** P2PKH transaction fundamentals
- **Chapter 3:** P2SH script engineering
- **Chapter 5:** Taproot evolution from SegWit

