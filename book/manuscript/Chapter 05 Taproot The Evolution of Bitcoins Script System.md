# Chapter 5: Taproot: The Evolution of Bitcoin's Script System

Taproot lets complex spending conditions look identical to simple payments on-chain: until the funds are spent, an elaborate script tree and a single-key payment are indistinguishable.

Two pieces of machinery make this possible, and this chapter takes them one at a time:

1. **Schnorr signatures (BIP340)** — a new signature scheme replacing ECDSA.
2. **Key tweaking (BIP341)** — a way to attach extra information to a public key without changing how it looks on-chain.

A few terms used below — `tweak`, `commitment`, `Merkle root`, `script path` — are stage-setting for Chapters 6–8. **If a phrase looks heavy on first read, skim it.** The same sentences will read differently after you've worked through Chapters 5–8. This chapter only assumes what Chapters 1–4 already gave you: keys, signatures, scripts, and witnesses.

## Schnorr Signatures

### Why Schnorr? The ECDSA Limitations

Bitcoin shipped with ECDSA in 2009 and has used it ever since. ECDSA is fine for signing and verifying transactions in isolation — but Taproot's design needs more than that. It needs signatures that don't drift when copied, that combine cleanly when multiple parties sign together, and that behave predictably under simple algebra. ECDSA was never built for any of those.

The properties of ECDSA that get in Taproot's way:

- **Malleability**: A third party can alter the encoding of a signature without invalidating it — the same signature, two on-chain forms.
- **No aggregation**: Two signatures from two parties stay as two separate signatures. They cannot be combined into one.
- **No linearity**: Adding two ECDSA signatures does not produce a valid signature for the sum of their keys. There is no clean algebra to build on.
- **Variable size**: 71–72 bytes typically, depending on encoding.

BIP340 specifies Schnorr signatures over the same secp256k1 curve, designed around the properties Taproot needs:

- **Non-malleable**: Deterministic nonces, x-only public keys, and strict encoding remove the third-party malleability vectors ECDSA suffers from.
- **Aggregatable**: Multiple public keys can be combined into one; multiple cooperating signers can produce a single 64-byte signature on-chain.
- **Linear**: This is the property that unlocks Taproot. We unpack it next.
- **Fixed 64 bytes**: Smaller and more uniform in size.

### Schnorr Linearity

The property that enables Taproot:

```
If Alice has signature A for message M
And Bob has signature B for the same message M  
Then A + B creates a valid signature for (Alice + Bob)'s combined key
```

From this, three capabilities follow:

1. **Key Aggregation**: Multiple people can combine their public keys into one
2. **Single-signature Output**: Multiple parties can cooperatively produce one single unified signature
3. **Key Tweaking**: Keys can be deterministically modified with commitments

> Note: "Single-signature output" refers to producing one BIP340 signature on-chain via MuSig2 (a wallet-level protocol), not a consensus-level signature aggregation across inputs.

### Visual Comparison: ECDSA vs Schnorr

```
ECDSA Multisig (3-of-3):
┌─────────────────────────────────────┐
│           Transaction               │
├─────────────────────────────────────┤
│ Alice Signature:   [71 bytes]       │
│ Bob Signature:     [72 bytes]       │
│ Charlie Signature: [70 bytes]       │
├─────────────────────────────────────┤
│ Total Size: ~213 bytes              │
│ Verifications: 3 separate           │
│ Privacy: reveals 3 participants     │
│ Appearance: multi                   │
└─────────────────────────────────────┘

Schnorr Aggregated (3-of-3):
┌─────────────────────────────────────┐
│           Transaction               │
├─────────────────────────────────────┤
│ Aggregated Signature: [64 bytes]    │
├─────────────────────────────────────┤
│ Total Size: 64 bytes                │
│ Verifications: 1 single check       │
│ Privacy: hides participant count    │
│ Appearance: single                  │
└─────────────────────────────────────┘
```

## Key Tweaking

Taproot leverages Schnorr's linearity through key tweaking (also called tweakable commitment in BIP340/341/342).

Conceptually: 

```
t = H("TapTweak" || internal_pubkey || merkle_root)
```

Formally (BIP341):

```
t  = int(HashTapTweak(xonly_internal_key || merkle_root_or_empty)) mod n

P' = P + t * G
d' = d + t
```

**Even-Y requirement (BIP340):**  
Taproot uses x-only public keys — but the actual point on secp256k1 still has two possible y values (even / odd).  
The BIP340 rule is: the final tweaked output key **must correspond to an even-y point**.  
If the point ends up odd-y, implementations flip the private key to `d' = n - d'` so that `P' = d'*G` lands on the even branch.

(Why this matters later: in script-path spending this parity is encoded into the control block's lowest bit. If you don't track this now, script-path won't verify later.)

### Tweak Flow

```
Internal Key (P) ─────────► + tweak ─────────► Output Key (P')
                              ▲                      │
                              │                      │
                       Merkle Root ◄─────────────────┘
                    script_path_commitment
```

Where:
- `P` = **Internal Key** (original public key, user controls)
- `M` = **Merkle Root** (commitment to all possible spending conditions)
- `t` = **Tweak Value** (deterministic from P and M)
- `P'` = **Output Key** (final Taproot address, appears on blockchain)
- `d'` = **Tweaked Private Key** (for key path spending)

### Practical Key Tweaking Implementation

```python
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from bitcoinutils.script import Script
import hashlib

def demonstrate_key_tweaking():
    setup('testnet')

    # Step 1: Generate internal key pair
    internal_private_key = PrivateKey('cTALNpTpRbbxTCJ2A5Vq88UxT44w1PE2cYqiB3n4hRvzyCev1Wwo')
    internal_public_key = internal_private_key.get_public_key()

    print("=== STEP 1: Internal Key Generation ===")
    print(f"Internal Private Key: {internal_private_key.to_wif()}")
    print(f"Internal Public Key:  {internal_public_key.to_hex()}")

    # Step 2: Create simple script commitment (we'll use empty for this example)
    # In real Taproot, this would be a Merkle root of script conditions
    script_commitment = b'' # Empty = key-path-only spending

    print(f"\n=== STEP 2: Script Commitment ===")
    print(f"Script Commitment: {script_commitment.hex() if script_commitment else 'Empty (key-path-only)'}")

    # Step 3: Calculate tweak using BIP341 formula
    internal_pubkey_bytes = bytes.fromhex(internal_public_key.to_x_only_hex()) # x-only
    tag_digest = hashlib.sha256(b'TapTweak').digest()
    tweak_preimage = tag_digest + tag_digest + internal_pubkey_bytes + script_commitment
    tweak_hash = hashlib.sha256(tweak_preimage).digest()
    tweak_int = int.from_bytes(tweak_hash, 'big')

    print(f"\n=== STEP 3: Tweak Calculation ===")
    print(f"Internal PubKey (x-only): {internal_pubkey_bytes.hex()}")
    print(f"Tweak Preimage: TapTweak || {internal_pubkey_bytes.hex()} || {script_commitment.hex()}")
    print(f"Tweak Hash: {tweak_hash.hex()}")
    print(f"Tweak Integer: {tweak_int}")

    # Step 4: Apply tweaking formula
    curve_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    internal_privkey_int = int.from_bytes(internal_private_key.to_bytes(), 'big')
    tweaked_privkey_int = (internal_privkey_int + tweak_int) % curve_order
    tweaked_private_key = PrivateKey.from_bytes(tweaked_privkey_int.to_bytes(32, 'big'))
    tweaked_public_key = tweaked_private_key.get_public_key()

    print(f"\n=== STEP 4: Tweaking Application ===")
    print(f"Original Private Key d: {internal_privkey_int}")
    print(f"Tweaked Private Key d': {tweaked_privkey_int}")
    print(f"Private Key Change: +{tweak_int}\n")
    print(f"Original Public Key P: {internal_public_key.to_hex()}")
    print(f"Tweaked Public Key P': {tweaked_public_key.to_hex()}")
    print(f"Public Key (x-only): {tweaked_public_key.to_hex()[2:]}")

    # Step 5: Verify the mathematical relationship
    print(f"\n=== STEP 5: Mathematical Verification ===")
    print(f"d' * G == P + tweak_int * G? {tweaked_public_key.to_x_only_hex() == internal_public_key.to_taproot_hex()[0]}")
    print(f"Anyone can compute P' from P and commitment: [OK]")
    print(f"Only key holder can compute d' from d and tweak: [OK]")

    return {
        'internal_private': internal_private_key,
        'internal_public': internal_public_key,
        'tweak_hash': tweak_hash,
        'tweaked_private': tweaked_private_key,
        'tweaked_public': tweaked_public_key
    }

# Execute the demonstration
result = demonstrate_key_tweaking()
```

The tweaked key produces two spending methods: the **key path**, where the tweaked private key signs directly, and the **script path**, where the internal public key plus a leaf script and control block prove that the leaf was committed in the Merkle root. Both paths produce the same on-chain output shape — `OP_1 <32-byte output key>` — and are indistinguishable until spent.

## A Simple Taproot Transaction

A basic Taproot-to-Taproot transaction:

```python
from bitcoinutils.setup import setup
from bitcoinutils.utils import to_satoshis
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.keys import PrivateKey, P2trAddress

def create_simple_taproot_transaction():
    setup('testnet')
    
    # Sender's information
    from_private_key = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
    from_pub = from_private_key.get_public_key()
    from_address = from_pub.get_taproot_address()
    
    # Receiver's address
    to_address = P2trAddress(
        'tb1p53ncq9ytax924ps66z6al3wfhy6a29w8h6xfu27xem06t98zkmvsakd43h'
    )
    
    print("=== TAPROOT TRANSACTION CREATION ===")
    print(f"From Address: {from_address.to_string()}")
    print(f"To Address: {to_address.to_string()}")
    
    # Create transaction input
    txin = TxInput(
        'b0f49d2f30f80678c6053af09f0611420aacf20105598330cb3f0ccb8ac7d7f0',
        0
    )
    
    # Input amount and script for signing
    input_amount = 0.00029200
    amounts = [to_satoshis(input_amount)]
    input_script = from_address.to_script_pub_key()
    scripts = [input_script]
    
    # Create transaction output
    amount_to_send = 0.00029000
    txout = TxOutput(
        to_satoshis(amount_to_send),
        to_address.to_script_pub_key()
    )
    
    # Create transaction with SegWit enabled
    tx = Transaction([txin], [txout], has_segwit=True)
    
    print(f"\nUnsigned Transaction:")
    print(tx.serialize())
    print(f"TxId: {tx.get_txid()}")
    
    # Sign the transaction using Schnorr signature
    # The sign_taproot_input() API handles the complex sighash construction:
    # 1. Builds BIP341 sighash with all input amounts and scripts
    # 2. Creates the signature message: sighash + key_version + code_separator
    # 3. Generates 64-byte Schnorr signature using tweaked private key
    sig = from_private_key.sign_taproot_input(
        tx,
        0,
        scripts,
        amounts
    )
    
    # Witness for key-path spend is the signature only; the public key is
    # already in the scriptPubKey as the output key.
    tx.witnesses.append(TxWitnessInput([sig]))
    
    # Get signed transaction
    signed_tx = tx.serialize()
    
    print(f"\nSigned Transaction:")
    print(signed_tx)
    
    print(f"\nTransaction Details:")
    print(f"Send Amount: {amount_to_send} BTC")
    print(f"Fee: {input_amount - amount_to_send} BTC")
    print(f"Transaction Size: {tx.get_size()} bytes")
    print(f"Virtual Size: {tx.get_vsize()} vbytes")
    
    return tx, sig

# Execute the transaction
tx, signature = create_simple_taproot_transaction()
```

`get_taproot_address()` applies the BIP341 tweak; `sign_taproot_input()` produces a 64-byte BIP340 signature. The witness stack item is 64 bytes, or 65 with a non-default sighash flag — `SIGHASH_DEFAULT` omits the flag.

## On-Chain Example: Testnet Taproot Transfer

Let's examine a real Taproot transaction: [`a3b4d038...57a42cb6`](https://mempool.space/testnet/tx/a3b4d0382efd189619d4f5bd598b6421e709649b87532d53aecdc76457a42cb6?showDetails=true)

**Transaction Structure:**

```
Input:
├── Previous Output: tb1pjyje...y3ku8
├── ScriptPubKey: OP_1 912591f3...5f697a3
└── Witness: [7d25fbc9...41da99f3]

Output:
├── Destination: tb1p53nc...akd43h
└── ScriptPubKey: OP_1 a3ff4d6e...7890ab
```

**Witness Data Analysis:**

```
Schnorr Signature: 7d25fbc9...41da99f3

Structure:
├── r-value: 7d25fbc9...2e30450d
├── s-value: 7d2a1f1d...41da99f3
└── Total: 64 bytes (32 + 32)
```

The signature is exactly 64 bytes with no variable encoding; the witness contains only the signature, with no public key (unlike SegWit).

## Key-Path Stack Execution

Trace of the stack for the transaction above:

### Initial State
The transaction begins with an empty stack:

```
│ (empty)                                 │
└─────────────────────────────────────────┘
```

### 1. OP_1: Push witness version
The scriptPubKey starts with OP_1, indicating this is a version 1 witness program:

```
│ 01 (witness_version)                    │
└─────────────────────────────────────────┘
```

### 2. PUSH Output Key: Load the 32-byte Taproot output key
The scriptPubKey pushes the 32-byte output key:

```
│ 912591f3...5f697a3 (output_key)         │
│ 01 (witness_version)                    │
└─────────────────────────────────────────┘
```

### 3. Pattern Recognition: Bitcoin Core detects Taproot format
The pattern `OP_1 <32-bytes>` selects the Taproot interpreter. A witness containing only a signature selects the key path; a witness containing a script and control block selects the script path (covered in Chapter 6).

### 4. Load Witness: Extract Schnorr signature
The witness stack contains only the signature:

```
│ 7d25fbc9...41da99f3 (schnorr_signature) │
│ 912591f3...5f697a3 (output_key)         │
└─────────────────────────────────────────┘
```

### 5. Schnorr Verification: Verify signature against output key
The interpreter runs BIP340 verification: parse `(r, s)`, compute the challenge `e = tagged_hash("BIP0340/challenge", r || P || m)`, compute `R = s·G - e·P`, and accept if `r` equals the x-coordinate of `R`.

**Verification Result:**

```
│ 1 (TRUE)                                │
└─────────────────────────────────────────┘
```

Verified — key-path spend.

## Output Shape: Legacy -> SegWit -> Taproot

```
Legacy P2PKH:
├── ScriptPubKey: OP_DUP OP_HASH160 <20-byte-hash> OP_EQUALVERIFY OP_CHECKSIG
├── ScriptSig: <signature> <public_key>
└── Size: ~225 bytes
   Information Revealed: Single signature spending

SegWit P2WPKH:
├── ScriptPubKey: OP_0 <20-byte-hash>
├── Witness: [signature, public_key]
└── Size: ~165 bytes
   Information Revealed: Single signature spending

Taproot P2TR (Simple):
├── ScriptPubKey: OP_1 <32-byte-output-key>
├── Witness: [schnorr_signature]
└── Size: ~135 bytes
   Information Revealed: Nothing about internal complexity

Taproot P2TR (Complex Contract):
├── ScriptPubKey: OP_1 <32-byte-output-key>
├── Witness: [schnorr_signature]
└── Size: ~135 bytes
   Information Revealed: Nothing about internal complexity
```

The simple-Taproot row and the complex-Taproot row are byte-for-byte identical at the output level.

## SegWit -> Taproot: Code Differences

```python
# SegWit (P2WPKH) Pattern
def create_segwit_transaction():
    private_key = PrivateKey(...)
    address = private_key.get_segwit_address()  # P2WPKH
    
    # Signing
    signature = private_key.sign_segwit_input(tx, 0, script_code, amount)
    
    # Witness: [signature, public_key]
    tx.witnesses.append(TxWitnessInput([signature, public_key]))

# Taproot (P2TR) Pattern  
def create_taproot_transaction():
    private_key = PrivateKey(...)
    public_key = private_key.get_public_key()
    address = public_key.get_taproot_address()  # P2TR
    
    # Signing
    signature = private_key.sign_taproot_input(tx, 0, scripts, amounts)
    
    # Witness: [signature] - No public key needed!
    tx.witnesses.append(TxWitnessInput([signature]))
```

Two API changes are load-bearing: signing uses `sign_taproot_input()` (Schnorr, BIP340) instead of `sign_segwit_input()` (ECDSA), and the witness contains only the signature — the public key is already in the scriptPubKey as the output key.

## Cooperative vs Script Path: Cost Asymmetry

Cooperative key-path spends produce a 64-byte witness regardless of how many parties are behind the output key. Script-path spends require revealing the leaf script and a control block (33 bytes for the internal pubkey + leaf depth * 32 bytes for the Merkle proof), so witness size scales with tree depth and revealed script length. The fee difference makes cooperation the cheaper path whenever it is available.

## Chapter Summary

Taproot replaces ECDSA with BIP340 Schnorr (64 bytes, fixed length) and applies the BIP341 tweak `P' = P + t·G` to the output key. The tweak commits to either nothing (key-path-only) or a Merkle root over a script tree. On-chain, both cases produce the same shape — `OP_1 <32 bytes>` — and a key-path spend has the same 64-byte witness regardless of internal complexity.

The next chapter shows how arbitrary spending conditions are organized into the script tree's Merkle structure, committed at output creation, and revealed only when actually used.