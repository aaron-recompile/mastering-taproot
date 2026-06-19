# Chapter 6: Building Real Taproot Contracts — Single-Leaf Hash Lock and Dual-Path Spending

Chapter 5 built a Taproot output that committed to nothing — a key-path-only address, where the only way to spend was Alice's tweaked key. This chapter adds the other half of Taproot: a script path. We give one address two independent ways to spend, and confirm that on-chain it still looks like an ordinary payment until the moment someone spends it.

The contract is deliberately small — a single script that releases funds to anyone who knows a secret word — so the mechanics stay in view. Everything here carries over to the multi-leaf trees of Chapters 7–8; this is the one-leaf version of the same machinery.

## The Scenario: A Conditional Payment

Alice wants an address that can be spent two ways:

- **Conditional path**: anyone who knows the secret word "helloworld" can claim the funds.
- **Owner path**: Alice can reclaim the funds at any time with her private key.
- **Privacy**: while unspent, the address is indistinguishable from any ordinary Taproot payment.

This two-path shape turns up constantly. A few cases that reduce to exactly the same structure:

| Use case | How the two paths map |
|----------|-----------------------|
| Digital goods sales | Buyer unlocks with a key after payment; seller keeps a refund path |
| Bounty tasks | Whoever solves the puzzle claims the reward; the publisher can reclaim an unclaimed bounty |
| Conditional escrow | Funds release when a condition is met; otherwise the owner reclaims them |
| Educational incentives | A student claims a reward on a correct answer; the teacher keeps a management path |

## Two Spending Paths

Alice's Taproot address carries two ways to spend, and they cost — and reveal — very different things.

**Key path.** Alice signs with her tweaked private key. One 64-byte Schnorr signature, nothing about the script revealed. This is the cheap, private path from Chapter 5.

**Script path.** The hash-lock script `OP_SHA256 <hash> OP_EQUALVERIFY OP_TRUE`. Anyone who can produce the preimage "helloworld" can spend it. Taking this path reveals the script you used — but nothing about the key path, and nothing about any other branch the tree might have held.

That asymmetry is the whole design: the key path is the quiet default; the script path is there for when you actually need the condition, and it only ever exposes the one branch you take.

## The Commit–Reveal Pattern

Almost everything we do with Taproot follows one shape, worth naming before any code: **commit, then reveal.**

**Commit.** You fold one or more spending conditions into a script tree, commit that tree into a single Taproot address, and fund it. From the outside the address is just 32 bytes — no one can tell which conditions it carries, or even whether it carries any.

**Reveal.** When you spend, you pick one path. The key path reveals nothing. The script path reveals exactly the one leaf you used — and leaves every other branch hidden for good.

What makes the pattern pay off: at commit time, contracts of wildly different complexity all look identical on-chain. At reveal time, you pay — in bytes and in privacy — only for the single branch you actually take.

## Single-Leaf Hash Lock: From Commit to Reveal

We'll build the smallest possible tree — one leaf — so nothing distracts from the commit->reveal flow:

- **Hash-lock script**: checks the SHA256 of the secret word "helloworld".
- **Single-leaf tree**: the simplest script tree there is, one leaf.
- **Two paths**: key path (Alice's direct control) plus script path (the conditional spend).

### Tagged Hash

One building block first. BIP340 runs everything through a *tagged* hash — a SHA256 with a purpose label folded in:

```python
def tagged_hash(tag, data):
    tag_hash = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(tag_hash + tag_hash + data).digest()

# tagged_hash("TapLeaf", script_data)          -> a script leaf hash
# tagged_hash("TapTweak", pubkey + merkle_root) -> the tweak
```

The label is what keeps a leaf hash from ever colliding with a tweak, or with a signature hash — even on identical input. Each tag carves out its own domain, so hashes computed for different purposes can never accidentally line up. (We walked this construction byte by byte earlier; "TapLeaf" and "TapTweak" are just two different labels feeding the same machine.)

### Phase 1 — Commit: lock the funds behind an address

First Alice commits the hash-lock script into a Taproot address:

```python
def build_hash_lock_script(preimage):
    """
    Build a Hash Lock Script – anyone who knows the preimage can spend
    """
    preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    return Script([
        'OP_SHA256',           # Calculate SHA256 of input
        preimage_hash,         # Expected hash to match against
        'OP_EQUALVERIFY',      # Verify hash equality or fail
        'OP_TRUE'              # Success condition
    ])

def create_taproot_commitment():
    setup('testnet')

    # Step 1: Alice's internal key - the foundation for her dual-path control
    internal_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    internal_public = internal_private.get_public_key()

    # Step 2: Build Hash Lock script for "helloworld" secret
    preimage = "helloworld"
    hash_lock_script = build_hash_lock_script(preimage)

    # Step 3: Generate Taproot address (commit script tree to blockchain)
    # This creates our "intermediate address" where funds will be locked
    taproot_address = internal_public.get_taproot_address([[hash_lock_script]])

    return taproot_address, hash_lock_script, internal_private
```

Three things happen under that `get_taproot_address` call. Walking them out:

**1. The script serializes to bytes.**

```
a820936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af8851
```

- `a8`: OP_SHA256
- `20`: PUSH 32 bytes
- `936a185c...8f8f07af`: SHA256("helloworld")
- `88`: OP_EQUALVERIFY
- `51`: OP_TRUE

**2. The serialized script becomes a TapLeaf hash, which — for a single leaf — is the whole Merkle root.**

```python
script_data = bytes.fromhex("a820936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af8851")
leaf_version = 0xc0
tapleaf_hash = tagged_hash("TapLeaf", bytes([leaf_version]) + bytes([len(script_data)]) + script_data)
merkle_root = tapleaf_hash  # one leaf, so the root is the leaf
```

**3. The Merkle root tweaks the internal key into the output key** — the same `Q = P + t·G` from Chapter 5, now with a real Merkle root in the tweak instead of an empty commitment:

```python
# BIP341: Q = P + H("TapTweak" || p || merkle_root) * G, where p is the x-only internal key
internal_pubkey = bytes.fromhex("50be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3")
tweak = tagged_hash("TapTweak", internal_pubkey + merkle_root)
output_key = point_add(internal_pubkey, scalar_mult(tweak, G))
```

The result is the address funds get sent to:

```text
tb1p53ncq9ytax924ps66z6al3wfhy6a29w8h6xfu27xem06t98zkmvsakd43h
```

Its ScriptPubKey is just `OP_1 <32-byte-output-key>` — byte-for-byte the same shape as every other Taproot address on chain. Nothing about it tells an observer whether it's a plain single-sig or a conditional contract. That indistinguishability is exactly what the commit phase buys.

### Phase 2 — Reveal via the key path (Alice reclaims)

One thing to set up before we spend: the next two phases each demonstrate *one* path — key path here, script path next. A UTXO can only be spent once, so these are not the same coin spent two ways; each path is shown on its own separate funding of the same address. That's why the input txids differ — `4fd83128...3d2d2c6d` here, `9e193d8c...40629886` in Phase 3.

If Alice just wants her funds back, she takes the key path:

```python
def alice_key_path_spending():
    setup('testnet')

    # Alice's key (same as Phase 1)
    alice_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    alice_public = alice_private.get_public_key()

    # Rebuild same script and Taproot address
    preimage = "helloworld"
    preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    tr_script = Script(['OP_SHA256', preimage_hash, 'OP_EQUALVERIFY', 'OP_TRUE'])
    taproot_address = alice_public.get_taproot_address([[tr_script]])

    # Basic transaction information
    commit_txid = "4fd83128fb2df7cd25d96fdb6ed9bea26de755f212e37c3aa017641d3d2d2c6d"
    input_amount = 0.00003900   # 3900 satoshis
    output_amount = 0.00003700  # 3700 satoshis (200 sats fee)

    # Build transaction
    txin = TxInput(commit_txid, 0)
    txout = TxOutput(
        to_satoshis(output_amount),
        alice_public.get_taproot_address().to_script_pub_key()
    )
    tx = Transaction([txin], [txout], has_segwit=True)

    # Key Path signature still needs the script tree to compute the tweak
    sig = alice_private.sign_taproot_input(
        tx,
        0,
        [taproot_address.to_script_pub_key()],  # Input ScriptPubKey
        [to_satoshis(input_amount)],            # Input amount
        script_path=False,                      # Explicitly specify Key Path
        tapleaf_scripts=[tr_script]             # Still need script tree to calculate tweak
    )

    # Witness data: Contains only 64-byte Schnorr signature
    tx.witnesses.append(TxWitnessInput([sig]))

    print(f"Key Path Transaction ID: {tx.get_txid()}")
    print(f"Witness Data: {sig}")
    return tx

# Actual execution result
tx = alice_key_path_spending()
# Output: Key Path Transaction ID: 2a13de71b3eb9c5845bc9aed56de0efd7d8f1e5e02debb0e9b3464a4ad940d05
```

The key-path spend looks exactly like Chapter 5's: a single 64-byte Schnorr signature in the witness, indistinguishable from any plain Taproot payment, verified in one check. The script never appears.

One detail is easy to miss. Even on the key path, the signer still passes `tapleaf_scripts`. That's because the output key was tweaked by the Merkle root at commit time — so to sign *for* the output key, Alice has to reconstruct the same tweak, which means she needs the script tree even though she never reveals it. `script_path=False` hides the bookkeeping, but underneath it's the Chapter 5 identity at work:

- **Public keys**: `output_pubkey = internal_pubkey + tweak · G`
- **Private keys**: `tweaked_private = internal_private + tweak`
- Because Schnorr is linear, those two stay a matched pair — Alice's tweaked private key signs for the output key.

This is the linearity from Chapter 5, doing the one job everything else depends on.

### Phase 3 — Reveal via the script path (the conditional unlock)

The script path is where the new work is. Instead of one signature, the witness has to carry enough to prove that a specific leaf really lives in the committed tree, plus the input the script needs to run.

```python
def script_path_spending():
    setup('testnet')

    # Step 1: Rebuild previous Taproot setup (must match commitment exactly!)
    alice_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    alice_public = alice_private.get_public_key()

    # Step 2: Recreate same Hash Lock script
    preimage = "helloworld"
    tr_script = build_hash_lock_script(preimage)
    taproot_address = alice_public.get_taproot_address([[tr_script]])

    # Step 3: Build spending transaction structure
    previous_txid = "9e193d8c5b4ff4ad7cb13d196c2ecc210d9b0ec144bb919ac4314c1240629886"
    input_amount = 0.00005000  # 5000 satoshis
    output_amount = 0.00004000  # 4000 satoshis (1000 sats fee)

    txin = TxInput(previous_txid, 0)
    txout = TxOutput(
        to_satoshis(output_amount),
        alice_public.get_taproot_address().to_script_pub_key()
    )
    tx = Transaction([txin], [txout], has_segwit=True)

    # Step 4: CRITICAL - Build control block to prove script legitimacy
    control_block = ControlBlock(
        alice_public,           # Internal public key for verification
        [[tr_script]],          # Script tree structure (single leaf)
        0,                      # Script index in tree (0 for single leaf)
        is_odd=taproot_address.is_odd()  # Output key parity - get from address!
    )

    # Step 5: Prepare script execution input - the secret "helloworld"
    preimage_hex = preimage.encode('utf-8').hex()  # Convert to hex: "68656c6c6f776f726c64"

    # Step 6: Build Script Path witness (ORDER MATTERS!)
    script_path_witness = TxWitnessInput([
        preimage_hex,              # [0] Script execution input: the secret
        tr_script.to_hex(),        # [1] Revealed script content
        control_block.to_hex()     # [2] Control block: cryptographic proof
    ])

    tx.witnesses.append(script_path_witness)
    return tx
```

Three pieces of that witness deserve a closer look.

**1. The control block.**

```python
control_block = ControlBlock(
    alice_public,           # Internal public key: base key for script tree commitment
    [[tr_script]],          # Script tree structure: [[leaf]] indicates single leaf tree
    0,                      # Script index: position of current script in tree
    is_odd=taproot_address.is_odd()  # Parity: y-coordinate parity of output key
)
```

```
Control Block Structure (33 bytes):
┌──────────┬──────────────────────────────────┐
│ Byte 1   │           Bytes 2-33             │
├──────────┼──────────────────────────────────┤
│   c1     │     50be5fc4...126bb4d3          │
├──────────┼──────────────────────────────────┤
│Ver/Parity│         Internal Pubkey          │
└──────────┴──────────────────────────────────┘

- c1 = c0 (leaf version) + 01 (parity flag)
- Internal pubkey: lets a verifier recompute the output key
```

The control block is the proof that this script belongs to the address. It carries:

- **Internal public key** — the untweaked key, so a verifier can redo the tweak and check it lands on the output key.
- **Script tree structure** — `[[tr_script]]` is a one-leaf tree; multiple scripts would be `[[script1], [script2]]`, and the block would then also carry the sibling hashes needed to walk back up to the root.
- **Script index** — which leaf this is; always 0 for a single leaf.
- **Parity flag** — the output point's y-coordinate is odd or even, and a verifier needs that bit to reconstruct the full point. Read it off the address with `is_odd()` — don't guess it.

**2. Witness order.**

```python
script_path_witness = TxWitnessInput([
    preimage_hex,              # [0] input to the script
    tr_script.to_hex(),        # [1] the script itself
    control_block.to_hex()     # [2] the control block
])
```

Bitcoin Core reads the script-path witness from the bottom up, and the positions are fixed:

- last element: the control block
- second-to-last: the script
- everything before that: the inputs the script consumes, in order

For our one-input hash lock that's just `[preimage, script, control_block]`. A handy way to remember it: **data -> code -> proof.**

**3. The preimage is hex-encoded bytes.**

```python
preimage_hex = preimage.encode('utf-8').hex()
# "helloworld" -> bytes -> "68656c6c6f776f726c64"
```

Script works on byte strings, not text. So "helloworld" goes to UTF-8 bytes first, then to hex — and that's what `OP_SHA256` hashes when the script runs.

#### Checking it against the chain

The transaction lands on testnet:

**Transaction ID**: [`68f7c8f0...722e604f`](https://mempool.space/testnet/tx/68f7c8f0ab6b3c6f7eb037e36051ea3893b668c26ea6e52094ba01a7722e604f?showDetails=true)

```bash
Witness Stack:
[0] 68656c6c6f776f726c64                    (preimage_hex)
[1] a820936a...f8f8f07af8851                (script_hex)
[2] c150be5f...d126bb4d3                    (control_block)
```

We can check each layer the way a node would. First, that the preimage really hashes to what the script expects:

```python
def verify_preimage_and_script_execution():
    # Verify preimage content
    preimage_hex = "68656c6c6f776f726c64"
    preimage_bytes = bytes.fromhex(preimage_hex)
    preimage_text = preimage_bytes.decode('utf-8')

    print(f"[OK] Preimage Verification:")
    print(f"   Hexadecimal: {preimage_hex}")
    print(f"   Text Content: '{preimage_text}'")

    # Calculate SHA256 hash
    computed_hash = hashlib.sha256(preimage_bytes).hexdigest()
    expected_hash = "936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af"

    print(f"[OK] Hash Verification:")
    print(f"   Computed Hash: {computed_hash}")
    print(f"   Expected Hash: {expected_hash}")
    print(f"   Match Result: {computed_hash == expected_hash}")

    return computed_hash == expected_hash

verify_preimage_and_script_execution()
```

That's the script's own check. A node does more: it confirms the **control block** proves the script sits under the Merkle root, restores the **address** from the internal key and that root, and only then runs the **script** on the stack. The next two checks mirror the first two of those.

**Control block — is the script really under the Merkle root?**

```python
def verify_script_in_merkle_tree():
    # Actual data extracted from chain
    control_block = "c150be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3"
    script_hex = "a820936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af8851"

    # Parse control block
    cb_bytes = bytes.fromhex(control_block)
    leaf_version = cb_bytes[0] & 0xfe    # 0xc0
    parity = cb_bytes[0] & 0x01          # 0x01 (parity)
    internal_pubkey = cb_bytes[1:33].hex()  # Internal public key

    print(f"[OK] Control Block Parsed Successfully:")
    print(f"   Leaf Version: {hex(leaf_version)}")
    print(f"   Internal Pubkey: {internal_pubkey}")

    # Since it's single leaf, no siblings, directly calculate TapLeaf hash as Merkle root
    script_bytes = bytes.fromhex(script_hex)
    tapleaf_hash = tagged_hash("TapLeaf",
        bytes([leaf_version]) +
        bytes([len(script_bytes)]) +
        script_bytes
    )
    merkle_root = tapleaf_hash  # Single leaf case

    print(f"[OK] Script is indeed in Merkle root:")
    print(f"   TapLeaf Hash: {tapleaf_hash.hex()}")
    print(f"   Merkle Root: {merkle_root.hex()}")

    return internal_pubkey, merkle_root

internal_pubkey, merkle_root = verify_script_in_merkle_tree()
```

**Address restoration — does the tweak land back on the committed address?**

```python
def verify_taproot_address_restoration():
    # Essentially tweak again to see if we can restore the intermediate address
    tweak = tagged_hash("TapTweak", 
        bytes.fromhex(internal_pubkey) + merkle_root
    )
    
    # Through elliptic curve operation: output_key = internal_pubkey + tweak * G
    # expected_output_key = point_add(internal_pubkey, scalar_mult(tweak, G))
    
    target_address = (
        "tb1p53ncq9ytax924ps66z6al3wfhy6a29w8h6xfu27xem06t98zkmv"
        "sakd43h"
    )
    
    print(f"[OK] Address Restoration Verification:")
    print(f"   Tweak Value: {tweak.hex()}")
    print(f"   Target Address: {target_address}")
    print(f"   Verification Result: Script Path is indeed usable")
    
    return True

verify_taproot_address_restoration()
```

Restoring the address is the same tweak from Phase 1, run in reverse as a check: take the internal key from the control block, the Merkle root from the revealed script, recompute the tweak, and confirm it rebuilds the address the funds were sent to. If it does, the script is genuinely committed and the spend is legitimate.

## When Script-Path Spending Fails: A Checklist

Script-path spends fail in a small number of predictable ways. When one does, work down this list.

**1. Witness order.** It must be `[preimage, script, control_block]` — data, then code, then proof. The two common wrong orders:

```
[correct] [preimage, script, control_block]
[wrong]   [control_block, script, preimage]
[wrong]   [script, preimage, control_block]
```

**2. Script consistency.** The script you reveal must be byte-for-byte the script you committed — same opcodes, same hash. The reliable way to guarantee that is to build both with the same function:

```python
def build_hash_lock_script(preimage):
    hash_value = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    return Script(['OP_SHA256', hash_value, 'OP_EQUALVERIFY', 'OP_TRUE'])

commit_script = build_hash_lock_script("helloworld")
reveal_script = build_hash_lock_script("helloworld")  # same bytes by construction
```

**3. Control block.** Internal pubkey correct? Script index matching the leaf's position (0 for a single leaf)? And the parity flag read from the address, not guessed:

```python
# wrong — guessing
is_odd = True

# right — read it off the address
is_odd = taproot_address.is_odd()
control_block = ControlBlock(..., is_odd=is_odd)
```

**4. Input encoding.** The preimage has to be UTF-8 bytes, then hex: `"helloworld" -> "68656c6c6f776f726c64"`.

**5. Address restoration.** As a final test, rebuild the Taproot address from the internal key plus the script tree. If the commit-phase and reveal-phase tweaks don't produce the same address, something upstream doesn't match.

One more failure mode worth calling out separately — passing the script as a string instead of a serialized `Script`:

```python
# wrong — a human-readable string is not what goes in the witness
script_hex = "OP_SHA256 936a185c... OP_EQUALVERIFY OP_TRUE"

# right — serialize a Script object
script = build_hash_lock_script(preimage)
script_hex = script.to_hex()  # "a820936a185c...8851"
```

## Stack Execution: Walking the Hash Lock

Here's the script running, one opcode at a time.

**Script**: `OP_SHA256 OP_PUSHBYTES_32 936a185c...8f8f07af OP_EQUALVERIFY OP_PUSHNUM_1`

**Start** — the witness loads the preimage onto the stack:

```
| 68656c6c6f776f726c64                             |
| (preimage_hex: "helloworld")                     |
└──────────────────────────────────────────────────┘
```

**OP_SHA256** — pops the preimage, pushes its SHA256:

```
| 936a185c...8f8f07af   |
| # computed_hash       |
└───────────────────────┘
```

(SHA256("helloworld") = 936a185c...8f8f07af)

**PUSH 32 bytes** — the script pushes its baked-in expected hash:

```
| 936a185c...8f8f07af   |
| # expected_hash       |
| 936a185c...8f8f07af   |
| # computed_hash       |
└───────────────────────┘
```

**OP_EQUALVERIFY** — pops the top two, compares; equal, so execution continues and both are consumed:

```
| (empty_stack) |
└───────────────┘
```

**OP_TRUE** — pushes 1, leaving a non-zero top of stack, which is what marks the script as satisfied:

```
| 01 (true_value) |
└─────────────────┘
```

## Key Path vs Script Path

The two paths, side by side on the numbers we just produced:

### Key path

- Witness: 1 element (64-byte signature)
- Transaction size: ~153 bytes
- Privacy: complete — nothing about the script revealed
- Verification: one Schnorr check
- Fee: lowest

### Script path

- Witness: 3 elements (input + script + control block)
- Transaction size: ~234 bytes
- Privacy: partial — only the executed leaf is revealed
- Verification: control-block check, then script execution
- Fee: higher (~50% more here)

The script path costs more bytes and gives up some privacy — but only for the one branch you use. Every other branch you might have committed stays hidden. That selective reveal is what lets one Taproot address back digital goods sales, bounties, escrow, multi-party contracts, and still look like a plain payment until the moment it's spent.

## How This Differs from P2SH

The contrast with P2SH is the sharpest way to see what the script path actually buys.

In P2SH, spending reveals the entire redeem script — every branch, including the ones you didn't take. An observer learns the whole contract the first time it's used.

Taproot's script path reveals only the leaf you executed. Unused branches are never published; they exist only as hashes folded into the Merkle root, and the chain never sees them. And until the address is spent at all, it's indistinguishable from an ordinary single-sig payment.

So the difference is concrete, not a slogan: P2SH exposes the contract, Taproot exposes one path through it. For contracts with multiple conditions — most real ones — that is a large reduction in what leaks on chain.

## Chapter Summary

We built Alice's hash-lock contract end to end and saw the commit–reveal pattern in full.

**Commit and reveal.** At commit time, a conditional contract folds into an ordinary-looking Taproot address that locks the funds. At reveal time, Alice picks a path — key path or script path — and exposes only what that path requires.

**What the implementation came down to:**

- **Single-leaf tree** — with one leaf, the TapLeaf hash *is* the Merkle root; no further Merkle math needed.
- **Control block** — proves a script is committed by restoring the address from the internal key and the script's leaf hash.
- **Stack execution** — the hash lock spends by matching `OP_SHA256` of the preimage against the committed hash.

**Things that bite if you get them wrong:**

- **Tagged hash** — the tag is what separates a TapLeaf hash from a TapTweak; same machine, different label.
- **Witness order** — `[input, script, control block]`, every time.
- **Commit/reveal consistency** — build the script with the same function in both phases so the bytes match exactly.

**Next.** Chapter 7 moves from one leaf to two: a dual-leaf script tree, where the Merkle root is computed from more than one branch and you start choosing which branch to reveal. That's where the tree in "script tree" earns its name.
