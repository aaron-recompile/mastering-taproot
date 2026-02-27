# Chapter 4: Building SegWit Transactions - From Construction to Stack Execution, and Witness Structure and Malleability Solutions

Segregated Witness (SegWit) fundamentally restructures Bitcoin transactions by separating signature data from transaction data. This chapter demonstrates SegWit's core innovations through a complete transaction implementation, from creation to broadcast, using real testnet data to trace the witness execution model that enables Taproot.

## 4.1 Transaction Malleability: The Problem SegWit Solves

### Legacy Transaction Structure vs SegWit

Traditional Bitcoin transactions bundle all data together for TXID calculation, while SegWit separates witness data:

```
Legacy Transaction Structure:
┌─────────────────────────────────────────┐
│ Version │ Inputs │ Outputs │ Locktime   │
│         │ ┌─────┐│         │            │
│         │ │ScSig││         │            │  } All included in TXID
│         │ │     ││         │            │
│         │ └─────┘│         │            │
└─────────────────────────────────────────┘
           ↓
    TXID = SHA256(SHA256(entire_transaction))


SegWit Transaction Structure:
┌─────────────────────────────────────────┐
│ Version │ Inputs │ Outputs │ Locktime   │  } Base Transaction
│         │ ┌─────┐│         │            │
│         │ │Empty││         │            │
│         │ │ScSig││         │            │
│         │ └─────┘│         │            │
└─────────────────────────────────────────┘
                                             } TXID = SHA256(SHA256(base_only))
┌─────────────────────────────────────────┐
│        Witness Data (Separated)         │  } Committed separately
│    ┌─────────────────────────────────┐  │
│    │ Signature │ Public Key          │  │  (For P2WPKH)
│    └─────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### The Malleability Problem Demonstrated

Before SegWit, attackers could modify signature encoding without affecting signature validity, but changing the TXID. The DER (Distinguished Encoding Rules) format used for ECDSA signatures allows for multiple valid encodings of the same signature. For example:

- **Original signature**: `304402201234567890abcdef...` (71 bytes)
- **Malleable version**: `3045022100001234567890abcdef...` (72 bytes with zero padding)

Both signatures are cryptographically identical and will pass ECDSA verification, but they have different byte representations. Since legacy Bitcoin includes the entire scriptSig (containing the signature) in the TXID calculation, these different encodings produce different transaction IDs for the same economic transaction.

This malleability breaks protocols that depend on specific TXIDs, particularly Lightning Network:

```
Lightning Channel Setup:
Funding TX (TXID_A) -> Commitment TX -> Timeout TX
                          ↓              ↓
                     References      References
                       TXID_A         TXID_B

If TXID_A changes due to malleability:
-> Commitment TX becomes invalid
-> Timeout TX becomes invalid  
-> Entire channel unusable
```

### Legacy vs SegWit Code Comparison

The programming model differences highlight the architectural change:

**Legacy P2PKH Signing:**
```python
# Legacy transaction signing
sk = PrivateKey(private_key_wif)
from_addr = P2pkhAddress(from_address)

# Create locking script for P2PKH
previous_locking_script = Script([
    "OP_DUP",
    "OP_HASH160", 
    from_addr.to_hash160(),
    "OP_EQUALVERIFY",
    "OP_CHECKSIG"
])

# Sign and set unlocking script
sig = sk.sign_input(tx, 0, previous_locking_script)
pk = sk.get_public_key().to_hex()
unlocking_script = Script([sig, pk])
tx_in.script_sig = unlocking_script  # Signature goes in scriptSig
```

**SegWit P2WPKH Signing:**
```python
# SegWit transaction signing
# CRITICAL: Must use sign_segwit_input, not sign_input
# Get script_code from public key's legacy address (required for SegWit)
script_code = public_key.get_address().to_script_pub_key()

signature = private_key.sign_segwit_input(
    tx,
    0,
    script_code,  # Legacy P2PKH format script code
    to_satoshis(utxo_amount)  # Input amount required for SegWit
)

# Set empty scriptSig (required for native SegWit)
txin.script_sig = Script([])

# Set witness data using TxWitnessInput wrapper
tx.witnesses.append(TxWitnessInput([signature, public_key.to_hex()]))
```

## 4.2 Creating a Complete SegWit Transaction

Let's build a real SegWit transaction step by step to understand how SegWit solves malleability through practical implementation.

### Transaction Setup

```python
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey, P2wpkhAddress
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.utils import to_satoshis
from bitcoinutils.script import Script

setup('testnet')

# Create keys and addresses
private_key = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
public_key = private_key.get_public_key()
from_address = public_key.get_segwit_address()
to_address = P2wpkhAddress('tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4')

print(f"From: {from_address.to_string()}")
print(f"To:   {to_address.to_string()}")
```

**Output:**
```
From: tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4
To:   tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4
```

**Note:** This example uses a real testnet transaction that was successfully broadcast. The transaction TXID is [`271cf628...6084e3e6`](https://mempool.space/testnet/tx/271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6?showDetails=true).

## 4.3 SegWit Transaction Construction and Analysis

### Step-by-Step Transaction Building

Let's build the transaction step by step, observing data structure changes at each phase:

### Phase 1: Create Unsigned Transaction

```python
# UTXO information (real testnet transaction)
utxo_txid = '1454438e6f417d710333fbab118058e2972127bdd790134ab74937fa9dddbc48'
utxo_vout = 0
utxo_amount = 1000  # sats

# Create transaction components
txin = TxInput(utxo_txid, utxo_vout)
txout = TxOutput(to_satoshis(0.00000666), to_address.to_script_pub_key())

# Build unsigned transaction (has_segwit=True required for witness data)
tx = Transaction([txin], [txout], has_segwit=True)
print(f"Unsigned TX: {tx.serialize()}")
```

**Unsigned Transaction Output:**
```text
0200000000010148bcdd9dfa3749b74a1390d7bd272197e2588011abfb3303717d41
6f8e4354140000000000fdffffff019a02000000000000160014c5b28d6bba91a269
3a9b1876bcd3929323890fb200000000
```

**Parsed Components:**
```
Version:      02000000
Marker:       00 (SegWit indicator)
Flag:         01 (SegWit version)
Input Count:  01
TXID:         1454438e...9dddbc48
VOUT:         00000000
ScriptSig:    00 (empty, 0 bytes)
Sequence:     fffffffd (RBF enabled - Replace-By-Fee)
Output Count: 01
Value:        9a02000000000000 (666 sats)
Script Len:   16 (22 bytes)
ScriptPubKey: 0014c5b28d6bba91a2693a9b1876bcd3929323890fb2
Locktime:     00000000
```

**Key Observations:**
- Standard Bitcoin transaction structure
- ScriptSig is empty (`00`) - this is normal for SegWit
- No witness data yet

### Phase 2: Add SegWit Signature

```python
# CRITICAL: Get script_code from public key's legacy address
# This must be in P2PKH format (76a914...88ac), not SegWit format
script_code = public_key.get_address().to_script_pub_key()

# Sign for SegWit using sign_segwit_input (not sign_input)
signature = private_key.sign_segwit_input(
    tx,
    0,
    script_code,  # Legacy P2PKH format script code
    to_satoshis(utxo_amount / 100000000)  # Input amount required
)

# Set empty scriptSig (required for native SegWit)
txin.script_sig = Script([])

# Set witness data using TxWitnessInput wrapper
public_key_hex = public_key.to_hex()
tx.witnesses.append(TxWitnessInput([signature, public_key_hex]))

# Check the differences
print(f"ScriptSig: '{txin.script_sig.to_hex()}'")  # Still empty
print(f"Witness Items: 2")
print(f"  [0] Signature: {signature[:20]}...{signature[-10:]}")
print(f"  [1] Public Key: {public_key_hex}")

# Complete signed transaction
signed_tx = tx.serialize()
print(f"Signed TX: {signed_tx}")
```

**Phase 2 Output:**
```
ScriptSig: ''
Witness Items: 2
  [0] Signature: 3044022015098d26918b...49e33c0301
  [1] Public Key: 02898711...74c8519
Signed TX:
0200000000010148bcdd9dfa3749b74a1390d7bd272197e2588011abfb3303717d41
6f8e4354140000000000fdffffff019a02000000000000160014c5b28d6bba91a269
3a9b1876bcd3929323890fb202473044022015098d26918b46ab36b0d1b50ee502b3
3d5c5b5257c76bd6d00ccb31452c25ae0220256e82d4df10981f25f91e5273be39fc
ed8fe164434616c94fa48f3549e33c03012102898711e6bf63f5cbe1b38c05e89d6c
391c59e9f8f695da44bf3d20ca674c851900000000
```

**Critical Changes:**
- ScriptSig remains empty
- Witness data appears
- Transaction becomes longer (added witness section)

### Transaction Structure Comparison

**Before Signing (Phase 1):**
```
Standard Bitcoin Transaction Format (with SegWit marker/flag)
├── Version: 02000000
├── Marker: 00 (SegWit indicator)
├── Flag: 01 (SegWit version)
├── Input Count: 01
├── Input Data: 48bcdd9d...00fdffffff (ScriptSig empty)
├── Output Count: 01  
├── Output Data: 9a020000...3890fb2
└── Locktime: 00000000

Total: 84 bytes (base transaction)
```

**After Signing (Phase 2):**
```
SegWit Transaction Format
├── Version: 02000000
├── Marker: 00 (SegWit indicator)
├── Flag: 01 (SegWit version)  
├── Input Count: 01
├── Input Data: 48bcdd9d...00fdffffff (ScriptSig still empty)
├── Output Count: 01
├── Output Data: 9a020000...3890fb2
├── Witness Data: 0247304402...c8519 (NEW - authorization data)
└── Locktime: 00000000

Total: 191 bytes (added witness section: 82 bytes)

**Note:** Sequence `0xfffffffd` indicates RBF (Replace-By-Fee) is enabled, allowing the transaction to be replaced with a higher fee if needed. This is why the chain explorer shows "RBF" in the transaction characteristics.
```
Note: marker/flag (00 01) appear only in the serialized form to indicate SegWit and do not participate in the txid (they do participate in the wtxid).

### Raw Transaction Parsed Components

**Complete Signed Transaction with Labeled Components:**
```
[VERSION]       02000000
[MARKER]        00      (SegWit indicator)
[FLAG]          01      (SegWit version)
[INPUT_COUNT]   01
[TXID]          1454438e...9dddbc48
[VOUT]          00000000
[SCRIPTSIG_LEN] 00      (Empty - authorization moved to witness)
[SEQUENCE]      fffffffd
[OUTPUT_COUNT]  01
[VALUE]         9a02000000000000  (666 satoshis)
[SCRIPT_LEN]    16      (22 bytes)
[SCRIPTPUBKEY]  0014c5b28d6bba91a2693a9b1876bcd3929323890fb2
[WITNESS_ITEMS] 02      (2 items: signature + public key)
[SIG_LEN]       47      (71 bytes)
[SIGNATURE]     30440220...49e33c0301
[PK_LEN]        21      (33 bytes)
[PUBLIC_KEY]    02898711...74c8519
[LOCKTIME]      00000000
```

## 4.4 P2WPKH Stack Execution Analysis

Now let's trace through the complete script execution using our real transaction data.

### Transaction Components

**Locking Script (ScriptPubKey):**
```
0014c5b28d6bba91a2693a9b1876bcd3929323890fb2
```

**Parsed:**
- `00`: OP_0 (witness version 0)
- `14`: Push 20 bytes
- `c5b28d6bba91a2693a9b1876bcd3929323890fb2`: Public key hash (20 bytes)

**Witness Stack (from real transaction):**
- Item 0: `30440220...49e33c0301` (signature, 71 bytes)
- Item 1: `02898711...74c8519` (public key, 33 bytes)

### SegWit Execution Model

Bitcoin Core recognizes the OP_0 <20-bytes> pattern and executes P2WPKH as equivalent to P2PKH:

**Effective Script:** `OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG`

### Stack Execution Trace

**Initial State:**
```
│ (empty)                                 │
└─────────────────────────────────────────┘
```

### 1. Load Witness Items onto Stack

```
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

### 2. Execute ScriptPubKey: OP_0 <pubkey_hash>

#### 2a. OP_0: Push witness version
```
│ 00 (witness_version)                    │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

#### 2b. PUSH PubKey Hash: Expected hash from script
```
│ c5b28d6bba91...890fb2 (expected_hash)   │
│ 00 (witness_version)                    │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

### 3. SegWit Interpreter: P2WPKH Pattern Recognition

**Bitcoin Core detects OP_0 <20-bytes> as P2WPKH and executes P2PKH-style verification:**

This is where SegWit's elegant design shines. When Bitcoin Core encounters a scriptPubKey that matches the pattern `OP_0 <20-byte-data>`, it recognizes this as a version 0 witness program with a 20-byte witness program (P2WPKH).

**The Pattern Recognition Process:**
1. **Version Detection**: `OP_0` indicates witness version 0
2. **Program Length Check**: 20 bytes indicates P2WPKH format
3. **Execution Mode Switch**: Bitcoin Core switches from normal script execution to witness program execution
4. **Equivalent Script Construction**: The interpreter treats the witness program as if it were executing: `OP_DUP OP_HASH160 <20-byte-pubkey-hash> OP_EQUALVERIFY OP_CHECKSIG`

**Why This Matters:**
This pattern recognition is crucial because it allows SegWit to maintain full backward compatibility while introducing new script semantics. Legacy nodes see `OP_0 <20-bytes>` and consider it anyone-can-spend (since OP_0 pushes an empty value, making the script evaluate to TRUE). SegWit nodes recognize the pattern and apply witness validation rules.

**The Execution Context Switch:**
Once the pattern is recognized, Bitcoin Core:
- Loads the witness stack items (signature and public key)
- Constructs the equivalent P2PKH script execution environment
- Validates that the public key hashes to the 20-byte witness program
- Verifies the signature against the transaction and public key

This pattern recognition framework is what enables Taproot's OP_1 programs—the same architectural principle extended to version 1 witness programs with 32-byte data.

#### 3a. OP_DUP: Duplicate public key
```
│ 02898711e6bf...c8519 (public_key)       │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

#### 3b. OP_HASH160: Hash public key
```
│ c5b28d6bba91...890fb2 (computed_hash)   │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```
**(Hash160 = RIPEMD160(SHA256(public_key)))**
In BIP143, the P2WPKH scriptCode used in the signature message is exactly the P2PKH template: `OP_DUP OP_HASH160 <20-byte-hash> OP_EQUALVERIFY OP_CHECKSIG`. This is why we derive `script_code` from `public_key.get_address().to_script_pub_key()` (legacy format: `76a914c5b2...890fb288ac`), not from the SegWit address.

#### 3c. PUSH Expected Hash: From witness program
```
│ c5b28d6bba91...890fb2 (expected_hash)   │
│ c5b28d6bba91...890fb2 (computed_hash)   │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

#### 3d. OP_EQUALVERIFY: Verify hash match
```
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```
**(Hash verification: computed_hash == expected_hash ✓)**

#### 3e. OP_CHECKSIG: Final signature verification
```
│ 1 (TRUE)                                │
└─────────────────────────────────────────┘
```
**(ECDSA signature verification against transaction data ✓)**

### Execution Result: SUCCESS

The P2WPKH spending is authorized with:
- [OK] Witness version valid (0)
- [OK] Public key hash matches witness program
- [OK] Signature verification passed
- [OK] Transaction malleability resistant (TXID excludes witness)

SegWit introduces two identifiers: the txid (hash of the base transaction, excludes witness) and the wtxid (includes witness). Miners commit the block’s witness data via the witness commitment (Merkle root of wtxids) in the coinbase.


## 4.5 SegWit to Taproot Evolution

SegWit establishes the architectural foundation that enables Taproot through three key innovations:

### Witness Version Framework
```
Version 0: P2WPKH (OP_0 <20-bytes>) and P2WSH (OP_0 <32-bytes>)
Version 1: P2TR (OP_1 <32-bytes>) - Taproot
```

### Malleability Resistance
Stable transaction IDs enable:
- Lightning Network channels
- Complex pre-signed transaction chains
- Reliable Layer 2 protocols

### Economic Incentives

SegWit introduces weight-based fee accounting:

```
Transaction Weight = (Base Size * 4) + Witness Size
Virtual Size = Weight ÷ 4
```
Intuition: Witness bytes are charged at 1 weight unit/byte while base bytes are 4 wu/byte. Savings depend on how much authorization data moves to witness (structure-dependent, not a fixed 25%/75%).

**Space Efficiency Through Separation:**

In legacy transactions, a 2-of-3 multisig requires a large scriptSig:
```
scriptSig: <empty> <sig1> <sig2> <redeemScript>
Total: ~300 bytes in scriptSig (counted at full weight)
```

In SegWit P2WSH, the same authorization moves to witness:
```
scriptSig: <empty> (0 bytes)
witness: <empty> <sig1> <sig2> <witnessScript>
Total: ~300 bytes in witness (75% discount)
```

This architectural change means complex scripts become economically viable. A SegWit multisig transaction pays approximately 25% less in fees compared to its legacy equivalent, while simple single-signature transactions see more modest savings.

**Taproot Amplification:**
SegWit's economic framework sets the stage for Taproot's even greater efficiencies. Taproot's one-signature on-chain via key aggregation can make complex multi-party arrangements as cheap as single-signature transactions, fully leveraging the witness discount structure that SegWit established.

## 4.6 Chapter Summary

This chapter demonstrated SegWit's core innovations through a complete transaction implementation:

**Witness Structure**: Separating signature data from transaction logic creates the foundation for Taproot's script trees and one-signature on-chain via key aggregation.

**Malleability Resistance**: Stable transaction IDs enable the Layer 2 ecosystem that Taproot optimizes with more efficient authorization schemes.

**Stack Execution Model**: The SegWit interpreter's pattern recognition for witness programs provides the template for Taproot's OP_1 execution model.

**Economic Framework**: Weight unit discounts create incentives for advanced script designs that Taproot maximizes through signature aggregation and script tree efficiency.

Understanding SegWit's witness architecture and execution model is essential for mastering Taproot because P2TR builds directly on these foundations while adding Schnorr signatures, key aggregation, and Merkle script trees.

In the next chapter, we'll explore how Schnorr signatures provide the mathematical primitives that enable Taproot's key aggregation and signature efficiency, building on SegWit's witness architecture to create Bitcoin's most advanced authorization schemes.