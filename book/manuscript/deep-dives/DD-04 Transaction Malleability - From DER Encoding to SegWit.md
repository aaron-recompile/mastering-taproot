# DD-4: Transaction Malleability — From DER Encoding to SegWit

> **Related chapters**: Chapter 4 (SegWit transactions), Chapter 11 (Lightning Network channels)
>
> **Prerequisites**: Understanding of ECDSA signatures and basic transaction structure (Chapters 1–4)

## Why This Deep Dive Exists

Chapter 4 introduces transaction malleability in a few paragraphs and moves on to SegWit construction. That's necessary — the main narrative needs to keep moving. But the malleability story deserves more: it's the single technical reason SegWit had to exist, and therefore the reason Taproot could exist. Without understanding *exactly* how a valid signature can be mutated into a different valid signature without anyone's private key, you can't fully appreciate why witness separation was not optional.

This Deep Dive does three things:

1. **Dissects DER encoding** — why ECDSA signatures have variable length, byte by byte
2. **Reproduces the attack** — Python code that takes a valid signature, flips the S value, and produces a different txid for the same economic transaction
3. **Connects to Lightning** — why this seemingly obscure encoding issue made payment channels impossible before SegWit

## Part 1: What Is DER Encoding?

### ECDSA Signatures Are Two Numbers

An ECDSA signature is a pair of integers `(r, s)`, each up to 256 bits (32 bytes). To embed them in a Bitcoin transaction, they must be serialized into a byte sequence. Bitcoin uses **DER** (Distinguished Encoding Rules), a subset of ASN.1.

### DER Format, Byte by Byte

```
30 <total_length>
  02 <r_length> <r_bytes>
  02 <s_length> <s_bytes>
<sighash_type>
```

A concrete example:

```
3044                          ← SEQUENCE, 68 bytes
  0220                        ← INTEGER, 32 bytes
    15098d26918b46ab36b0d1b5  ← r value (32 bytes)
    0ee502b33d5c5b5257c76bd6
    d00ccb31452c25ae
  0220                        ← INTEGER, 32 bytes
    256e82d4df10981f25f91e52  ← s value (32 bytes)
    73be39fced8fe164434616c9
    4fa48f3549e33c03
01                            ← SIGHASH_ALL
```

Total: 71 bytes (this one). But it could be 70, 71, 72, or even 73 bytes for the same `(r, s)` pair. Here's why:

### Why the Length Varies

DER integers are **signed** big-endian. Two rules create variability:

**Rule 1: High-bit padding.** If the first byte of `r` or `s` has its high bit set (≥ 0x80), DER requires a leading `0x00` byte to indicate the number is positive. So the same 32-byte integer might serialize as 32 or 33 bytes.

```
r = 0x7f...  → r_length = 32 (no padding needed)
r = 0x80...  → r_length = 33 (0x00 prefix added)
r = 0xff...  → r_length = 33 (0x00 prefix added)
```

**Rule 2: Leading zero stripping.** DER's minimal encoding rules require stripping leading zero bytes (except the sign byte). So if `r` starts with `0x00`, the DER encoding drops it.

```
r = 0x00a1...  → encoded as 0xa1... (31 bytes, no leading zero)
```

These two rules mean the total signature length varies between ~70 and ~73 bytes, depending on the specific `r` and `s` values.

### Code Experiment 1: Parse a Real DER Signature

```python
def parse_der_signature(sig_hex: str) -> dict:
    """Parse a DER-encoded ECDSA signature byte by byte."""
    sig = bytes.fromhex(sig_hex)
    pos = 0
    result = {}
    
    # SEQUENCE tag
    assert sig[pos] == 0x30, f"Expected SEQUENCE tag 0x30, got {sig[pos]:#04x}"
    pos += 1
    
    # Total length of r + s
    total_len = sig[pos]
    result['total_length'] = total_len
    pos += 1
    
    # Parse r
    assert sig[pos] == 0x02, f"Expected INTEGER tag 0x02, got {sig[pos]:#04x}"
    pos += 1
    r_len = sig[pos]
    pos += 1
    r_bytes = sig[pos:pos + r_len]
    result['r_length'] = r_len
    result['r'] = r_bytes.hex()
    result['r_has_padding'] = (r_len == 33 and r_bytes[0] == 0x00)
    pos += r_len
    
    # Parse s
    assert sig[pos] == 0x02, f"Expected INTEGER tag 0x02, got {sig[pos]:#04x}"
    pos += 1
    s_len = sig[pos]
    pos += 1
    s_bytes = sig[pos:pos + s_len]
    result['s_length'] = s_len
    result['s'] = s_bytes.hex()
    result['s_has_padding'] = (s_len == 33 and s_bytes[0] == 0x00)
    pos += s_len
    
    # Sighash type (last byte, not part of DER)
    if pos < len(sig):
        result['sighash'] = sig[pos]
    
    result['total_bytes'] = len(sig)
    return result

# Real signature from Chapter 4's testnet transaction
sig_hex = ("3044022015098d26918b46ab36b0d1b50ee502b33d5c5b5257c76bd6d00ccb31"
           "452c25ae0220256e82d4df10981f25f91e5273be39fced8fe164434616c94fa4"
           "8f3549e33c0301")

parsed = parse_der_signature(sig_hex)
print("===== DER Signature Parsing =====")
print(f"Total bytes: {parsed['total_bytes']}")
print(f"DER payload length: {parsed['total_length']}")
print(f"r ({parsed['r_length']} bytes): {parsed['r']}")
print(f"  High-bit padding: {parsed['r_has_padding']}")
print(f"s ({parsed['s_length']} bytes): {parsed['s']}")
print(f"  High-bit padding: {parsed['s_has_padding']}")
print(f"Sighash type: {parsed.get('sighash', 'N/A'):#04x}")
print(f"\nSignature length breakdown:")
print(f"  30 + len + 02 + r_len + r + 02 + s_len + s + sighash")
print(f"  1  + 1   + 1  + 1     + {parsed['r_length']}+ 1  + 1     + {parsed['s_length']}+ 1")
print(f"  = {1+1+1+1+parsed['r_length']+1+1+parsed['s_length']+1} bytes total")
```

## Part 2: The S-Value Malleability Attack

### The Mathematical Loophole

ECDSA verification checks whether `(r, s)` is a valid signature for message `m` under public key `P`. But there's a mathematical identity on the secp256k1 curve:

**If `(r, s)` is a valid signature, then `(r, n - s)` is also a valid signature for the same message and public key**, where `n` is the curve order.

This is because ECDSA verification involves computing `s⁻¹`, and:

```
(n - s)⁻¹ ≡ -s⁻¹ (mod n)
```

The negation flips a point to its y-axis mirror on the curve, but the x-coordinate (which is what `r` represents) stays the same. So both signatures pass verification.

### Why This Matters for Bitcoin

In Legacy Bitcoin transactions, the signature lives in `scriptSig`, which is included in the TXID hash:

```
TXID = SHA256(SHA256( version | inputs[scriptSig included] | outputs | locktime ))
```

If someone — a miner, a relay node, anyone who sees the transaction in the mempool — replaces `s` with `n - s`, the transaction is still valid (ECDSA verification passes), but the TXID changes because the bytes in scriptSig changed.

**The attacker doesn't need the private key.** They just flip a number.

### Code Experiment 2: Flip the S Value, Change the TXID

```python
import hashlib

SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

def flip_s_value(sig_hex: str) -> str:
    """
    Take a DER-encoded signature, replace s with (n - s),
    and re-encode in DER format. Returns the malleable signature.
    """
    sig = bytes.fromhex(sig_hex)
    
    # Parse to find s
    pos = 0
    assert sig[pos] == 0x30
    pos += 1
    total_len = sig[pos]
    pos += 1
    
    # Skip r
    assert sig[pos] == 0x02
    pos += 1
    r_len = sig[pos]
    pos += 1
    r_bytes = sig[pos:pos + r_len]
    pos += r_len
    
    # Parse s
    assert sig[pos] == 0x02
    pos += 1
    s_len = sig[pos]
    pos += 1
    s_bytes = sig[pos:pos + s_len]
    pos += s_len
    
    # Get sighash type
    sighash = sig[pos] if pos < len(sig) else None
    
    # Convert s to integer and flip
    s_int = int.from_bytes(s_bytes, 'big')
    s_flipped = SECP256K1_ORDER - s_int
    
    print(f"Original s:  {s_int:#066x}")
    print(f"Flipped s:   {s_flipped:#066x}")
    print(f"Curve order: {SECP256K1_ORDER:#066x}")
    
    # Check: which s is "low"?
    half_order = SECP256K1_ORDER // 2
    print(f"Original s {'<=' if s_int <= half_order else '>'} n/2 "
          f"({'low-S ✓' if s_int <= half_order else 'high-S ✗'})")
    print(f"Flipped  s {'<=' if s_flipped <= half_order else '>'} n/2 "
          f"({'low-S ✓' if s_flipped <= half_order else 'high-S ✗'})")
    
    # Re-encode flipped s in DER
    s_flipped_bytes = s_flipped.to_bytes(32, 'big').lstrip(b'\x00')
    # Add high-bit padding if needed
    if s_flipped_bytes[0] >= 0x80:
        s_flipped_bytes = b'\x00' + s_flipped_bytes
    
    # Rebuild DER
    new_s_len = len(s_flipped_bytes)
    new_total_len = 2 + r_len + 2 + new_s_len  # 02+r_len+r + 02+s_len+s
    
    der = bytes([0x30, new_total_len,
                 0x02, r_len]) + r_bytes + \
          bytes([0x02, new_s_len]) + s_flipped_bytes
    
    if sighash is not None:
        der += bytes([sighash])
    
    return der.hex()


def double_sha256(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


# ===== Demonstrate the attack =====
print("===== S-Value Malleability Attack =====\n")

# Original signature from Chapter 4's testnet transaction
original_sig = ("3044022015098d26918b46ab36b0d1b50ee502b33d5c5b5257c76bd6d00ccb31"
                "452c25ae0220256e82d4df10981f25f91e5273be39fced8fe164434616c94fa4"
                "8f3549e33c0301")

print("Step 1: Flip the S value")
print("-" * 50)
malleable_sig = flip_s_value(original_sig)

print(f"\nOriginal signature ({len(original_sig)//2} bytes):")
print(f"  {original_sig}")
print(f"\nMalleable signature ({len(malleable_sig)//2} bytes):")
print(f"  {malleable_sig}")
print(f"\nLength change: {len(original_sig)//2} → {len(malleable_sig)//2} bytes")

# ===== Show TXID change =====
print(f"\n\nStep 2: Observe the TXID change")
print("-" * 50)

# Simulate a Legacy transaction with the signature in scriptSig
# This is a simplified demonstration — in a real transaction,
# the full serialized tx bytes would differ

# Build a minimal fake Legacy tx skeleton with original sig
def build_fake_legacy_tx(sig_hex: str) -> bytes:
    """Build a minimal Legacy tx with the signature in scriptSig."""
    version = bytes.fromhex("02000000")
    input_count = bytes.fromhex("01")
    prev_txid = bytes.fromhex(
        "48bcdd9dfa3749b74a1390d7bd272197e2588011abfb3303717d416f8e435414")
    prev_vout = bytes.fromhex("00000000")
    
    sig_bytes = bytes.fromhex(sig_hex)
    pubkey = bytes.fromhex(
        "02898711e6bf63f5cbe1b38c05e89d6c391c59e9f8f695da44bf3d20ca674c8519")
    
    # scriptSig: <sig_len> <sig> <pubkey_len> <pubkey>
    scriptsig = bytes([len(sig_bytes)]) + sig_bytes + \
                bytes([len(pubkey)]) + pubkey
    scriptsig_with_len = bytes([len(scriptsig)]) + scriptsig
    
    sequence = bytes.fromhex("fdffffff")
    output_count = bytes.fromhex("01")
    value = bytes.fromhex("9a02000000000000")
    scriptpubkey = bytes.fromhex("160014c5b28d6bba91a2693a9b1876bcd3929323890fb2")
    scriptpubkey_with_len = bytes([len(scriptpubkey)]) + scriptpubkey
    locktime = bytes.fromhex("00000000")
    
    tx = (version + input_count + prev_txid + prev_vout +
          scriptsig_with_len + sequence +
          output_count + value + scriptpubkey_with_len + locktime)
    return tx

tx_original = build_fake_legacy_tx(original_sig)
tx_malleable = build_fake_legacy_tx(malleable_sig)

txid_original = double_sha256(tx_original)[::-1].hex()
txid_malleable = double_sha256(tx_malleable)[::-1].hex()

print(f"TXID (original sig):  {txid_original}")
print(f"TXID (flipped sig):   {txid_malleable}")
print(f"TXIDs are different:  {txid_original != txid_malleable}")
print(f"\nSame economic transaction (same inputs, same outputs, same amounts)")
print(f"Both signatures are cryptographically valid")
print(f"But different TXIDs — this is transaction malleability")
```

**What this demonstrates:**

1. We take a real signature from a testnet transaction
2. We flip `s` to `n - s` — no private key needed
3. We rebuild the signature in DER format
4. The resulting DER bytes are different (and possibly a different length)
5. A Legacy transaction containing this mutated signature has a different TXID
6. Both transactions are equally valid — any node will accept either one

### Code Experiment 3: Verify Both Signatures Are Valid

```python
from coincurve import PrivateKey, PublicKey
import hashlib

print("===== Verifying Both Signatures =====\n")

# Generate a key pair for demonstration
privkey = PrivateKey(hashlib.sha256(b"demo_malleability_key").digest())
pubkey = privkey.public_key
message = hashlib.sha256(b"test transaction data").digest()

# Sign the message
sig_der = privkey.sign(message, hasher=None)  # Returns DER-encoded

# Parse r and s from the DER signature
def extract_r_s(der_sig: bytes) -> tuple:
    pos = 2  # skip 0x30 + length
    assert der_sig[pos] == 0x02
    r_len = der_sig[pos + 1]
    r = int.from_bytes(der_sig[pos + 2:pos + 2 + r_len], 'big')
    pos = pos + 2 + r_len
    assert der_sig[pos] == 0x02
    s_len = der_sig[pos + 1]
    s = int.from_bytes(der_sig[pos + 2:pos + 2 + s_len], 'big')
    return r, s

r, s = extract_r_s(sig_der)
s_flipped = SECP256K1_ORDER - s

# Re-encode the flipped signature in DER
def encode_der(r: int, s: int) -> bytes:
    def int_to_der_bytes(n: int) -> bytes:
        b = n.to_bytes(32, 'big').lstrip(b'\x00') or b'\x00'
        if b[0] >= 0x80:
            b = b'\x00' + b
        return b
    
    r_bytes = int_to_der_bytes(r)
    s_bytes = int_to_der_bytes(s)
    payload = b'\x02' + bytes([len(r_bytes)]) + r_bytes + \
              b'\x02' + bytes([len(s_bytes)]) + s_bytes
    return b'\x30' + bytes([len(payload)]) + payload

sig_original = encode_der(r, s)
sig_malleable = encode_der(r, s_flipped)

# Verify both
valid_original = pubkey.verify(sig_original, message, hasher=None)
valid_malleable = pubkey.verify(sig_malleable, message, hasher=None)

print(f"Original signature:  {sig_original.hex()}")
print(f"  Length: {len(sig_original)} bytes")
print(f"  Valid:  {valid_original}")
print(f"\nMalleable signature: {sig_malleable.hex()}")
print(f"  Length: {len(sig_malleable)} bytes")
print(f"  Valid:  {valid_malleable}")
print(f"\nBoth valid: {valid_original and valid_malleable}")
print(f"Bytes differ: {sig_original != sig_malleable}")

print(f"\n===== The Core Problem =====")
print(f"Anyone who sees a transaction in the mempool can:")
print(f"  1. Extract the signature from scriptSig")
print(f"  2. Flip s to (n - s)")
print(f"  3. Re-broadcast with the new signature")
print(f"  4. The mutated version might get mined instead")
print(f"  5. Same funds move, but different TXID")
print(f"  6. Any protocol that referenced the original TXID breaks")
```

## Part 3: Why Lightning Had to Wait for SegWit

### The Dependency Chain Problem

Lightning Network channels work by building a chain of pre-signed transactions, each referencing the previous one by TXID:

```
Funding TX (TXID: abc123)
  └── Output 0: 2-of-2 multisig [Alice + Bob]

Commitment TX (spends abc123:0)
  ├── Output 0: to_local (Bob's balance, delayed)
  └── Output 1: to_remote (Alice's balance)

HTLC-Timeout TX (spends commitment output)
  └── Returns timed-out HTLC to sender
```

Every transaction in this chain references a specific TXID from the previous transaction. If any TXID changes, the entire chain breaks:

```
Before malleability attack:
  Funding TX: abc123 → Commitment TX (references abc123) ✓

After malleability attack:
  Funding TX mined as: def456 (same tx, different TXID)
  Commitment TX still references: abc123 ✗ INVALID
  
  Result: Funds locked forever — Bob and Alice cannot close the channel
```

### The Concrete Scenario

1. Alice and Bob create a funding transaction (TXID: `abc123`)
2. Before broadcasting, they pre-sign commitment transactions that reference `abc123`
3. Alice broadcasts the funding transaction
4. A miner (or relay node) modifies the signature's S value
5. The funding transaction gets mined with TXID `def456`
6. The pre-signed commitment transactions reference `abc123` — which doesn't exist on-chain
7. The channel's funds are locked in the 2-of-2 multisig with no way to spend them

Alice and Bob could cooperate to sign new commitment transactions referencing `def456`. But:

- They might not be online at the same time
- They might not agree (one party could hold the other hostage)
- The entire security model of the channel is compromised — you can't pre-sign anything with confidence

**This isn't a theoretical attack.** Before SegWit, transaction malleability was actively exploited. The Mt. Gox exchange blamed malleability for discrepancies in their withdrawal tracking system (though the full picture was more complex). More importantly, any serious multi-transaction protocol was fundamentally impossible.

### How SegWit Fixes It

SegWit's solution is elegant: **move the signature out of the TXID calculation**.

```
Legacy TXID:  SHA256(SHA256( version | inputs_with_scriptSig | outputs | locktime ))
                                           ↑
                                    Signature is HERE
                                    Changing it changes TXID

SegWit TXID:  SHA256(SHA256( version | inputs_with_empty_scriptSig | outputs | locktime ))
                                           ↑
                                    scriptSig is EMPTY
                                    Signature is in witness (separate)
                                    Changing witness does NOT change TXID
```

The signature still exists (in the witness section), and nodes still verify it. But it's no longer part of the TXID hash input. Flip S all you want — the TXID stays the same.

This is why Chapter 4 shows `txin.script_sig = Script([])` — that empty scriptSig is the entire point. It's not a quirk of the API; it's the architectural innovation that made Lightning possible.

### Code Experiment 4: SegWit TXID Is Immune

```python
print("===== SegWit TXID Immunity =====\n")

# In SegWit, TXID is computed from the "base transaction" (no witness)
# Let's show this explicitly

def build_segwit_base_tx() -> bytes:
    """Build the base (non-witness) serialization for TXID computation."""
    version = bytes.fromhex("02000000")
    input_count = bytes.fromhex("01")
    prev_txid = bytes.fromhex(
        "48bcdd9dfa3749b74a1390d7bd272197e2588011abfb3303717d416f8e435414")
    prev_vout = bytes.fromhex("00000000")
    scriptsig_len = bytes.fromhex("00")  # EMPTY — this is the key
    sequence = bytes.fromhex("fdffffff")
    output_count = bytes.fromhex("01")
    value = bytes.fromhex("9a02000000000000")
    scriptpubkey = bytes.fromhex("160014c5b28d6bba91a2693a9b1876bcd3929323890fb2")
    scriptpubkey_with_len = bytes([len(scriptpubkey)]) + scriptpubkey
    locktime = bytes.fromhex("00000000")
    
    return (version + input_count + prev_txid + prev_vout +
            scriptsig_len + sequence +
            output_count + value + scriptpubkey_with_len + locktime)

base_tx = build_segwit_base_tx()
segwit_txid = double_sha256(base_tx)[::-1].hex()

print(f"SegWit base transaction (for TXID): {base_tx.hex()}")
print(f"SegWit TXID: {segwit_txid}")
print(f"\nNote: the signature is NOT in this serialization")
print(f"No matter how you modify the witness data,")
print(f"this TXID stays the same.")
print(f"\nThis is why Lightning works:")
print(f"  Funding TX TXID is stable")
print(f"  → Commitment TXs can safely reference it")
print(f"  → HTLC TXs can safely reference commitment TXs")
print(f"  → The entire pre-signed transaction chain is reliable")
```

## Part 4: BIP66 and Low-S — Partial Fixes Before SegWit

SegWit wasn't the first attempt to address malleability. Two earlier measures reduced the attack surface:

### BIP66: Strict DER Encoding (2015)

Before BIP66, Bitcoin accepted non-standard DER encodings. Some implementations would accept signatures with unnecessary leading zeros, non-minimal length bytes, or even non-DER formats. BIP66 mandated strict DER compliance, eliminating encoding-level malleability.

### BIP62 / Low-S Policy (Standardness Rule)

Bitcoin Core adopted a policy rule (not consensus) requiring `s ≤ n/2` (the "low-S" value). Since both `s` and `n - s` are valid, and exactly one of them is ≤ `n/2`, this convention picks a canonical form. Miners following this policy won't include transactions with high-S values, making S-value flipping ineffective in practice.

```
s ≤ n/2  → "low-S"  → accepted by standard policy
s > n/2  → "high-S" → rejected by standard policy (but valid by consensus)
```

### Why These Weren't Enough

BIP66 + low-S policy mitigated the *most common* malleability vectors, but:

1. **Policy ≠ Consensus**: A miner could still include high-S transactions in a block. Policy rules are enforced by relay nodes but not by the consensus layer.
2. **Other malleability vectors exist**: `OP_0` vs empty push, extra stack items in `OP_CHECKMULTISIG` — the scriptSig-in-TXID architecture is fundamentally fragile.
3. **Third-party malleability remains**: Even with strict rules, anyone can modify a scriptSig before it's mined. Only the signer can produce a valid signature, but the *encoding* of that signature can be manipulated.

SegWit eliminated the root cause: it removed signatures from the TXID computation entirely.

## Part 5: From Malleability to Taproot

The connection from malleability to Taproot runs through three steps:

```
Malleability → SegWit (witness separation)
  → Witness versioning (version 0, version 1, ...)
    → Taproot = witness version 1

Without malleability, no SegWit.
Without SegWit, no witness versioning.
Without witness versioning, no clean upgrade path to Taproot.
```

But Taproot goes further. Schnorr signatures (BIP340) use **x-only public keys** and always produce **exactly 64-byte signatures** — no DER encoding at all:

```
ECDSA (DER): 30 <len> 02 <r_len> <r> 02 <s_len> <s> → 70–73 bytes, variable
Schnorr:     <r: 32 bytes> <s: 32 bytes>              → 64 bytes, always

No DER means:
  ✓ No encoding variability
  ✓ No high-S / low-S ambiguity (Schnorr uses implicit parity)
  ✓ Simpler verification code
  ✓ Smaller witness data
```

Taproot's fixed-size signatures close out the encoding-variability problem this Deep Dive started with. The steps from DER-encoded ECDSA to 64-byte Schnorr signatures span about a decade:

```
2009: Bitcoin launches with DER-encoded ECDSA in scriptSig
2011: First malleability concerns raised
2014: Mt. Gox collapse, malleability cited as contributing factor
2015: BIP66 (strict DER) activated
2017: SegWit activated — signatures removed from TXID
2021: Taproot activated — DER encoding eliminated entirely
```

## Summary

| Concept | Legacy | SegWit v0 | Taproot (SegWit v1) |
|---------|--------|-----------|---------------------|
| Signature encoding | DER (variable length) | DER (variable length) | Raw 64 bytes (fixed) |
| Signature in TXID | Yes | No | No |
| S-value malleability | Exploitable | Not in TXID | Not possible (Schnorr) |
| Pre-signed tx chains | Unreliable | Reliable | Reliable |
| Lightning possible | No | Yes | Yes (improved) |

Transaction malleability is not an abstract cryptographic curiosity — it's the reason Bitcoin's scripting system had to be re-architected. Understanding it byte-by-byte is understanding why SegWit exists, why Lightning works, and why Taproot's clean-slate signature scheme was worth the effort.

## Exercises

### Exercise 1: Parse Real Signatures
1. Take 5 different testnet transactions from mempool.space
2. Extract their DER-encoded signatures
3. Parse each one and record the r_length and s_length
4. How many are 70, 71, 72, or 73 bytes?

### Exercise 2: Manual S-Value Flip
1. Take a real DER signature
2. Manually flip the S value (compute n - s)
3. Re-encode in DER
4. Verify both signatures using `coincurve`

### Exercise 3: TXID Stability Test
1. Build a Legacy-style transaction and compute its TXID
2. Flip the S value in the signature
3. Compute the new TXID — confirm they differ
4. Build a SegWit transaction and compute its TXID
5. Confirm the SegWit TXID does not change regardless of witness mutations

### Exercise 4: Measure Signature Size Distribution
1. Write a script that generates 1,000 ECDSA signatures
2. DER-encode each one and record the length
3. Plot or tabulate the distribution of lengths
4. What percentage are 70, 71, 72, or 73 bytes?
5. Compare: Schnorr signatures are always exactly 64 bytes
