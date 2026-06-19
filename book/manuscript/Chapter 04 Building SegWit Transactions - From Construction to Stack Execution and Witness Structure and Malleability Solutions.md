# Chapter 4: Building SegWit Transactions — Construction, Stack Execution, and Malleability

Segregated Witness (SegWit) separates signature data from the rest of a transaction. This chapter builds one real SegWit transaction end to end — construct, sign, serialize, and trace its execution — using testnet data, and shows how that separation fixes malleability and sets up the witness model Taproot later builds on.

## 4.1 Transaction Malleability: The Problem SegWit Solves

### Legacy Transaction Structure vs SegWit

A legacy transaction hashes everything together to get its TXID. SegWit moves the witness out of that hash:

```
Legacy Transaction Structure:
┌─────────────────────────────────────────┐
│ Version │ Inputs │ Outputs │ Locktime   │
│         │ ┌─────┐│         │            │
│         │ │ScSig││         │            │  } All included in TXID
│         │ │     ││         │            │
│         │ └─────┘│         │            │
└─────────────────────────────────────────┘
           v
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
│    ┌─────────────────────────────────┐  │      (For P2WPKH)
│    │ Signature │ Public Key          │  │
│    └─────────────────────────────────┘  │
└─────────────────────────────────────────┘
           v
    WTXID = SHA256(SHA256(entire_transaction[base + witness]))
```

That single change — witness data out of the TXID — is what removes malleability. The next section shows why the old structure was malleable in the first place.

### The Malleability Problem

Before SegWit, a third party could re-encode a signature without breaking it, and in doing so change the transaction's TXID. ECDSA signatures are serialized with DER (Distinguished Encoding Rules), and the same signature has more than one valid DER encoding. For example:

- **Original signature**: `304402201234567890abcdef...` (71 bytes)
- **Malleable version**: `3045022100001234567890abcdef...` (72 bytes with zero padding)

Both encodings verify as the same signature, but their bytes differ. Because legacy Bitcoin folds the whole scriptSig — signature included — into the TXID, the two encodings give the same economic transaction two different TXIDs.

That breaks any protocol that pins a later transaction to an earlier TXID — Lightning most of all:

```
Lightning Channel Setup:
Funding TX (TXID_A) -> Commitment TX -> Timeout TX
                          v              v
                     References      References
                       TXID_A         TXID_B

If TXID_A changes due to malleability:
-> Commitment TX becomes invalid
-> Timeout TX becomes invalid  
-> Entire channel unusable
```

Pre-signed transaction chains like this assume the funding TXID is fixed. Malleate it and every transaction built on top is orphaned.

### Legacy vs SegWit Code Comparison

The change shows up directly in how you sign. In legacy P2PKH, the signature goes into the scriptSig:

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

In SegWit P2WPKH, the scriptSig stays empty and the signature goes into the witness. Two details matter: you call `sign_segwit_input` (not `sign_input`), and SegWit signing needs the input amount:

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

Two things to flag for later: the `script_code` comes from the *legacy* P2PKH form of the key, and the input amount is now part of what's signed. Both are BIP143 requirements, and we'll see why each appears when we trace execution in §4.4.

## 4.2 Creating a Complete SegWit Transaction

We'll build one real SegWit transaction step by step, watching the bytes change at each phase.

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

The from and to addresses are the same here — this is a self-send, which keeps the example to one key.

**Note:** This is a real testnet transaction that was successfully broadcast: [`271cf628...6084e3e6`](https://mempool.space/testnet/tx/271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6?showDetails=true).

## 4.3 SegWit Transaction Construction and Analysis

### Phase 1: Create the Unsigned Transaction

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

Even unsigned, the transaction already carries the SegWit marker/flag (`00 01`) and an empty scriptSig. There's no witness yet — that's the next phase.

### Phase 2: Add the SegWit Signature

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

The scriptSig is still empty; everything authorizing the spend now lives in the witness section appended at the end.

### Transaction Structure: Before and After

**Before signing (Phase 1):**

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

**After signing (Phase 2):**

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

Total: 191 bytes (added witness section: 107 bytes)
```

**Note:** Sequence `0xfffffffd` enables RBF (Replace-By-Fee), so the transaction can later be replaced by a higher-fee version — which is why explorers tag it "RBF".

**Note:** the marker/flag (`00 01`) appear only in the serialized form to signal SegWit. They do not participate in the txid (they do participate in the wtxid).

### Raw Transaction, Component by Component

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

## 4.4 P2WPKH Stack Execution

Now trace the spend through the script interpreter, using the real transaction's data.

### The Pieces

**Locking script (ScriptPubKey):**

```
0014c5b28d6bba91a2693a9b1876bcd3929323890fb2
```

**Parsed:**
- `00`: OP_0 (witness version 0)
- `14`: push 20 bytes
- `c5b28d6bba91a2693a9b1876bcd3929323890fb2`: public key hash (20 bytes)

**Witness stack (from the real transaction):**
- Item 0: `30440220...49e33c0301` (signature, 71 bytes)
- Item 1: `02898711...74c8519` (public key, 33 bytes)

### How P2WPKH Executes

A P2WPKH locking script is just `OP_0 <20-byte-hash>`. When Bitcoin Core sees that pattern — witness version 0, a 20-byte program — it doesn't run a normal script. It recognizes P2WPKH and runs the equivalent P2PKH check against the witness items:

**Effective script:** `OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG`

This recognition is what keeps SegWit backward-compatible. A legacy node sees `OP_0 <20-bytes>` and reads it as anyone-can-spend (OP_0 leaves a truthy-enough script), so it relays the transaction without understanding it; a SegWit node recognizes the pattern and enforces the witness rules. The same mechanism, extended to version 1 with a 32-byte program (`OP_1 <32-bytes>`), is exactly how Taproot outputs are recognized in Chapter 5 onward.

### Stack Execution Trace

**Initial state:**

```
│ (empty)                                 │
└─────────────────────────────────────────┘
```

**Load the witness items:**

```
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

**OP_0 — push witness version:**

```
│ 00 (witness_version)                    │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

**Push the pubkey hash from the script:**

```
│ c5b28d6bba91...890fb2 (expected_hash)   │
│ 00 (witness_version)                    │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

At this point the interpreter switches into the P2PKH-equivalent execution described above, loading the signature and public key from the witness and running `OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG`:

**OP_DUP — duplicate the public key:**

```
│ 02898711e6bf...c8519 (public_key)       │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

**OP_HASH160 — hash the public key:**

```
│ c5b28d6bba91...890fb2 (computed_hash)   │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

Hash160 = RIPEMD160(SHA256(public_key)). Under BIP143, the scriptCode signed for P2WPKH is exactly this P2PKH template — `OP_DUP OP_HASH160 <20-byte-hash> OP_EQUALVERIFY OP_CHECKSIG` — which is why §4.1 derived `script_code` from `public_key.get_address().to_script_pub_key()` (legacy form `76a914c5b2...890fb288ac`), not from the SegWit address.

**Push the expected hash from the witness program:**

```
│ c5b28d6bba91...890fb2 (expected_hash)   │
│ c5b28d6bba91...890fb2 (computed_hash)   │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

**OP_EQUALVERIFY — the two hashes must match:**

```
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

computed_hash == expected_hash [OK]

**OP_CHECKSIG — verify the signature:**

```
│ 1 (TRUE)                                │
└─────────────────────────────────────────┘
```

ECDSA verification of the signature against the transaction [OK]

### Result

The spend authorizes: witness version 0, the public key hashes to the 20-byte program, the signature checks out — and because the TXID excludes the witness, the transaction is no longer malleable.

SegWit gives a transaction two identifiers: the **txid** (hash of the base transaction, witness excluded) and the **wtxid** (witness included). Miners commit the block's witness data through a witness commitment — a Merkle root of wtxids — placed in the coinbase.

## 4.5 From SegWit to Taproot

Three things SegWit established are what Taproot builds on directly.

**The witness-version framework.** SegWit defines outputs by version and program length, leaving room for later versions:

```
Version 0: P2WPKH (OP_0 <20-bytes>) and P2WSH (OP_0 <32-bytes>)
Version 1: P2TR (OP_1 <32-bytes>) - Taproot
```

Taproot is just witness version 1 with a 32-byte program — the next slot in the framework this chapter traced.

**Malleability resistance.** Stable TXIDs are what make pre-signed transaction chains safe to build — Lightning channels and other Layer 2 protocols depend on it.

**Weight-based fees.** SegWit charges witness bytes less than base bytes:

```
Transaction Weight = (Base Size * 4) + Witness Size
Virtual Size = Weight / 4
```

Base bytes cost 4 weight units each; witness bytes cost 1. So moving authorization data into the witness lowers its weight. How much you actually save depends on how much of the transaction is authorization data — it's structure-dependent, not a fixed percentage.

For a 2-of-3 multisig the difference is large, because the authorization is large. In legacy form it sits in the scriptSig, counted at full weight:

```
scriptSig: OP_0 <sig1> <sig2> <redeemScript>
Total: ~300 bytes in scriptSig (counted at full weight)
```

In SegWit P2WSH the same data moves to the witness, where each byte costs a quarter:

```
scriptSig: <empty> (0 bytes)
witness: OP_0 <sig1> <sig2> <witnessScript>
Total: ~300 bytes in witness (charged at 1 wu/byte)
```

The more of a transaction that is authorization data, the more the witness discount helps — which is why complex scripts benefit most. Taproot pushes this further still: with key aggregation, a multi-party spend can put a single 64-byte signature on chain, paying close to what a single-signer transaction pays. That's Chapter 5 onward.

## 4.6 Chapter Summary

We built one SegWit transaction from construction to execution, and saw the four things that carry forward into Taproot:

- **Witness structure** — separating the signature from the transaction body is the split that script trees and key aggregation later build on.
- **Malleability resistance** — taking the witness out of the TXID stabilizes transaction IDs, which is what pre-signed Layer 2 protocols require.
- **Execution by pattern** — the interpreter recognizes `OP_0 <20-bytes>` and runs the equivalent P2PKH check; Taproot's `OP_1 <32-bytes>` is the same idea one version up.
- **Weight-based fees** — charging witness bytes less rewards moving authorization data off the base transaction.

P2TR builds straight on all four, adding Schnorr signatures, key aggregation, and Merkle script trees.

### What Chapters 1–4 covered

This chapter closes the foundational part of the book. The first four chapters are the Bitcoin that exists before Taproot:

- **Chapter 1** — private keys, public keys, and how addresses encode them.
- **Chapter 2** — Script and the stack: how a P2PKH output locks and unlocks.
- **Chapter 3** — P2SH: committing to a redeem script, with multisig and timelocks built on top.
- **Chapter 4** — SegWit: moving the witness out of the transaction body, which fixes malleability.

Everything Taproot does is a variation on these four — keys and signatures, scripts that run on a stack, commitments to a script, and the witness model. If any of them feels shaky, it's worth shoring up before Chapter 5, because the next four chapters lean on all of them at once.

### Chapters 5–8: Taproot itself

The second part of the book is Taproot proper, built up one mechanism at a time the same way:

- **Chapter 5** — Schnorr signatures and the key tweak.
- **Chapter 6** — a single-leaf script path.
- **Chapter 7** — two leaves and a real Merkle root.
- **Chapter 8** — four leaves, a two-level tree, multisig and timelocks.

Chapters 9–12 then turn to applications — Ordinals, RGB, Lightning, and Silent Payments.

**Next.** Chapter 5 starts with Schnorr signatures — the scheme whose linearity makes key aggregation and the key tweak possible, the first piece of Taproot.
