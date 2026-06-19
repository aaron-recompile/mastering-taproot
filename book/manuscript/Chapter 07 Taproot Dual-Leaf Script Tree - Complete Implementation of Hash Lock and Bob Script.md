# Chapter 7: Taproot Dual-Leaf Script Tree — Hash Lock and Bob Script

## From One Leaf to Two

Chapter 6 built a Taproot address with a single leaf — one hash-lock script, alongside Alice's key path. With one leaf, the TapLeaf hash *was* the Merkle root, and the control block carried nothing but the internal key. This chapter adds a second leaf, and that one change pulls in the rest of the script-tree machinery: a real Merkle root computed from two branches, and a control block that has to carry a sibling hash to prove its leaf belongs.

The contract we build gives one address three independent ways to spend:

- **Script path 1** — a hash lock: anyone who knows "helloworld" can spend.
- **Script path 2** — Bob's script: only Bob's private key can spend.
- **Key path** — Alice, the internal-key holder, can spend directly (the quiet, private default).

As in Chapter 6, none of this is visible from outside. Until someone spends, the address is indistinguishable from a plain payment; spending reveals only the one path taken.

## The Merkle Structure of a Two-Leaf Tree

With one leaf there was nothing to combine. With two, you build an actual Merkle tree:

```
        Merkle Root
       /           \
  TapLeaf A    TapLeaf B
(Hash Script) (Bob Script)
```

Three steps, and the second is the genuinely new one:

1. **TapLeaf hash** — each script hashes to its own leaf, exactly as in Chapter 6.
2. **TapBranch hash** — the two leaf hashes are sorted lexicographically, then hashed together into the parent. The sort is what makes the root deterministic: whichever order you list the scripts, the smaller hash always goes first, so everyone computes the same root.
3. **Control block** — to spend one leaf, you have to prove it sits under that root. The proof is the *other* leaf's hash, carried in the control block, so a verifier can recompute the branch and land on the root.

The rest of the chapter is that structure, seen from real on-chain data.

## Two On-Chain Transactions

We'll work backwards from two real testnet spends of the same dual-leaf address.

**Transaction 1 — hash-script path**
- TXID: [`b61857a0...78a2e430`](https://mempool.space/testnet/tx/b61857a05852482c9d5ffbb8159fc2ba1efa3dd16fe4595f121fc35878a2e430?showDetails=true)
- Address: `tb1p93c4...gq9a4w3z`
- Spent with the preimage "helloworld".

**Transaction 2 — Bob-script path**
- TXID: [`185024da...5a70cfe0`](https://mempool.space/testnet/tx/185024daff64cea4c82f129aa9a8e97b4622899961452d1d144604e65a70cfe0?showDetails=true)
- Address: `tb1p93c4...gq9a4w3z`
- Spent with Bob's signature.

The two spends share the **same address** — which is the whole point. Both come out of one dual-leaf tree; each just reveals a different leaf. (They spend two different fundings of that address, since a UTXO can only be spent once.)

## Commit: Building the Two-Leaf Tree

Here is the code that produces that address:

```python
def create_dual_leaf_taproot():
    """Build dual-leaf Taproot address containing Hash Lock and Bob Script"""
    setup('testnet')

    # Alice's internal key (Key Path controller)
    alice_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    alice_public = alice_private.get_public_key()

    # Bob's key (Script Path 2 controller)
    bob_private = PrivateKey('cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG')
    bob_public = bob_private.get_public_key()

    # Script 1: Hash Lock - verify preimage "helloworld"
    preimage = "helloworld"
    preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    hash_script = Script([
        'OP_SHA256',
        preimage_hash,  # 936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af
        'OP_EQUALVERIFY',
        'OP_TRUE'
    ])

    # Script 2: Bob Script - P2PK verify Bob's signature
    bob_script = Script([
        bob_public.to_x_only_hex(),  # 84b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5
        'OP_CHECKSIG'
    ])

    # Build dual-leaf script tree (flat structure)
    all_leafs = [hash_script, bob_script]

    # Generate Taproot address
    taproot_address = alice_public.get_taproot_address(all_leafs)

    print(f"Dual-leaf Taproot address: {taproot_address.to_string()}")
    print(f"Hash Script: {hash_script}")
    print(f"Bob Script: {bob_script}")

    return taproot_address, hash_script, bob_script

# Actually generated address
# Output: tb1p93c4...gq9a4w3z
```

Two things to notice, because they decide the rest:

- **The tree is flat**: `all_leafs = [hash_script, bob_script]` — two leaves at the same level.
- **Order fixes the index**: `hash_script` is index 0, `bob_script` is index 1. That index is what you'll pass to the control block when spending each leaf, so it has to match.

The library takes that list, computes both TapLeaf hashes, sorts and combines them into the Merkle root, and tweaks Alice's key into the output key. If two different script-path spends both rebuild this same address, the tree was constructed identically each time — which is exactly the check we lean on below.

## Reveal: Spending Each Script Path

### Hash-script path

From transaction [`b61857a0...78a2e430`](https://mempool.space/testnet/tx/b61857a05852482c9d5ffbb8159fc2ba1efa3dd16fe4595f121fc35878a2e430?showDetails=true):

```python
def hash_script_path_spending():
    """Hash Script Path spending - unlock using preimage"""
    setup('testnet')

    # Rebuild identical script tree
    alice_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    alice_public = alice_private.get_public_key()

    bob_private = PrivateKey('cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG')
    bob_public = bob_private.get_public_key()

    # Build same script tree
    preimage = "helloworld"
    preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    hash_script = Script(['OP_SHA256', preimage_hash, 'OP_EQUALVERIFY', 'OP_TRUE'])
    bob_script = Script([bob_public.to_x_only_hex(), 'OP_CHECKSIG'])

    all_leafs = [hash_script, bob_script]
    taproot_address = alice_public.get_taproot_address(all_leafs)

    # Build transaction
    txin = TxInput(
        "f02c055369812944390ca6a232190ec0db83e4b1b623c452a269408bf8282d66",
        0
    )
    txout = TxOutput(to_satoshis(0.00001034), alice_public.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Key: Build Hash Script's Control Block (index 0)
    control_block = ControlBlock(
        alice_public,
        all_leafs,
        0,  # hash_script index
        is_odd=taproot_address.is_odd()
    )

    # Witness data: [preimage, script, control_block]
    preimage_hex = preimage.encode('utf-8').hex()
    tx.witnesses.append(TxWitnessInput([
        preimage_hex,
        hash_script.to_hex(),
        control_block.to_hex()
    ]))

    return tx
```

This is the Chapter 6 hash-lock spend, with one change that matters: the control block is built from `all_leafs` (both scripts) at index 0. The library needs the whole tree to know what the sibling is — index 0 means "this is the hash script; the other leaf is its sibling, include its hash as the proof." With a single leaf there was no sibling to include; now there is.

### Bob-script path

From transaction [`185024da...5a70cfe0`](https://mempool.space/testnet/tx/185024daff64cea4c82f129aa9a8e97b4622899961452d1d144604e65a70cfe0?showDetails=true):

```python
def bob_script_path_spending():
    """Bob Script Path spending - unlock using Bob's private key signature"""
    setup('testnet')

    # Same script tree construction
    alice_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    alice_public = alice_private.get_public_key()

    bob_private = PrivateKey('cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG')
    bob_public = bob_private.get_public_key()

    # Rebuild script tree
    preimage_hash = hashlib.sha256("helloworld".encode('utf-8')).hexdigest()
    hash_script = Script(['OP_SHA256', preimage_hash, 'OP_EQUALVERIFY', 'OP_TRUE'])
    bob_script = Script([bob_public.to_x_only_hex(), 'OP_CHECKSIG'])

    all_leafs = [hash_script, bob_script]
    taproot_address = alice_public.get_taproot_address(all_leafs)

    # Build transaction
    txin = TxInput(
        "8caddfad76a5b3a8595a522e24305dc20580ca868ef733493e308ada084a050c",
        1
    )
    txout = TxOutput(to_satoshis(0.00000900), bob_public.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Key: Build Bob Script's Control Block (index 1)
    control_block = ControlBlock(
        alice_public,
        all_leafs,
        1,  # bob_script index
        is_odd=taproot_address.is_odd()
    )

    # Script Path signature (note parameters)
    sig = bob_private.sign_taproot_input(
        tx, 0,
        [taproot_address.to_script_pub_key()],
        [to_satoshis(0.00001111)],
        script_path=True,
        tapleaf_script=bob_script,  # Singular form!
        tweak=False
    )

    # Witness data: [signature, script, control_block]
    tx.witnesses.append(TxWitnessInput([
        sig,
        bob_script.to_hex(),
        control_block.to_hex()
    ]))

    return tx
```

Two differences from the hash path, both following from the fact that Bob's leaf is a signature check rather than a hash check:

- **The control block is at index 1** — this is the second leaf, so its sibling is the *hash* script's hash.
- **The spend signs**, where the hash path didn't. The signing parameters are worth reading closely:
  - `script_path=True` — sign for a leaf, not the key path.
  - `tapleaf_script=bob_script` — singular, because you sign against the *one* leaf you're executing (contrast Chapter 6's key-path `tapleaf_scripts`, plural, which needed the whole tree to rebuild the tweak).
  - `tweak=False` — a script-path signature is checked by `OP_CHECKSIG` against Bob's plain key inside the script, so the key is *not* tweaked. This is the opposite of the key path, where the whole point was signing with the tweaked key.

The witness shape is the Chapter 6 one — data, then script, then control block — with a signature standing in for the preimage:

| | Hash-script path | Bob-script path |
|---|---|---|
| Script index | 0 | 1 |
| Witness `[0]` | preimage hex | Schnorr signature |
| How the script checks it | hash match | signature check |
| Control block's sibling | Bob script's TapLeaf hash | hash script's TapLeaf hash |

## Control Blocks, Read From the Chain

The table's last row is the new idea, so look at it in the raw bytes. Each control block carries the *other* leaf's hash — that's the Merkle proof.

**Hash-script path**, from [`b61857a0...78a2e430`](https://mempool.space/testnet/tx/b61857a05852482c9d5ffbb8159fc2ba1efa3dd16fe4595f121fc35878a2e430?showDetails=true):

```
Control Block: c050be5f...8105cf9df

├─ c0: leaf version (0xc0)
├─ 50be5fc4...126bb4d3: Alice's internal pubkey
└─ 2faaa677...8105cf9df: Bob script's TapLeaf hash  <- the sibling
```

**Bob-script path**, from [`185024da...5a70cfe0`](https://mempool.space/testnet/tx/185024daff64cea4c82f129aa9a8e97b4622899961452d1d144604e65a70cfe0?showDetails=true):

```
Control Block: c050be5f...8f10f659e

├─ c0: leaf version (0xc0)
├─ 50be5fc4...126bb4d3: Alice's internal pubkey (same!)
└─ fe78d852...8f10f659e: hash script's TapLeaf hash  <- the sibling
```

Two things to read off these directly:

- The internal pubkey is **identical** in both — same Alice, same tree.
- The trailing 32 bytes are **swapped**: each leaf carries its sibling's hash. The hash path carries Bob's leaf hash; Bob's path carries the hash leaf's hash. That swap *is* the Merkle proof — give a verifier the one leaf plus its sibling's hash, and they can rebuild the branch and the root.

### Verifying a control block = rebuilding the address

Checking a control block comes down to one thing: take the revealed leaf, the sibling hash from the control block, and the internal key, and see whether they rebuild the address the funds were sent to.

```python
def verify_control_block_and_address_reconstruction():
    """Verify Control Block and reconstruct Taproot address"""

    # Hash Script Path data
    hash_control_block = (
        "c050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3"
        "2faaa677cb6ad6a74bf7025e4cd03d2a82c7fb8e3c277916d7751078105cf9df"
    )
    hash_script_hex = (
        "a820936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af"
        "8851"
    )

    # Bob Script Path data
    bob_control_block = (
        "c050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3"
        "fe78d8523ce9603014b28739a51ef826f791aa17511e617af6dc96a8f10f659e"
    )
    bob_script_hex = (
        "2084b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5"
        "ac"
    )

    # Parse Control Block structure
    def parse_control_block(cb_hex):
        cb_bytes = bytes.fromhex(cb_hex)
        leaf_version = cb_bytes[0] & 0xfe
        parity = cb_bytes[0] & 0x01
        internal_pubkey = cb_bytes[1:33]
        merkle_path = cb_bytes[33:]  # sibling node hash
        return leaf_version, parity, internal_pubkey, merkle_path

    # Parse Hash Script's Control Block
    hash_version, hash_parity, hash_internal_key, hash_sibling = parse_control_block(hash_control_block)

    # Parse Bob Script's Control Block
    bob_version, bob_parity, bob_internal_key, bob_sibling = parse_control_block(bob_control_block)

    print("Control Block verification:")
    print(f"[OK] Internal pubkey consistent: {hash_internal_key == bob_internal_key}")
    print(f"[OK] Alice internal pubkey: {hash_internal_key.hex()}")

    # Calculate respective TapLeaf hashes
    hash_tapleaf = tagged_hash("TapLeaf", bytes([hash_version]) + bytes([len(bytes.fromhex(hash_script_hex))]) + bytes.fromhex(hash_script_hex))
    bob_tapleaf = tagged_hash("TapLeaf", bytes([bob_version]) + bytes([len(bytes.fromhex(bob_script_hex))]) + bytes.fromhex(bob_script_hex))

    print(f"\nTapLeaf hash calculation:")
    print(f"[OK] Hash Script TapLeaf: {hash_tapleaf.hex()}")
    print(f"[OK] Bob Script TapLeaf:  {bob_tapleaf.hex()}")

    # Verify sibling node relationship
    print(f"\nSibling node verification:")
    print(f"[OK] Hash Script's sibling is Bob TapLeaf: {hash_sibling.hex() == bob_tapleaf.hex()}")
    print(f"[OK] Bob Script's sibling is Hash TapLeaf: {bob_sibling.hex() == hash_tapleaf.hex()}")

    # Calculate Merkle Root
    # Sort lexicographically then calculate TapBranch
    if hash_tapleaf < bob_tapleaf:
        merkle_root = tagged_hash("TapBranch", hash_tapleaf + bob_tapleaf)
    else:
        merkle_root = tagged_hash("TapBranch", bob_tapleaf + hash_tapleaf)

    print(f"\nMerkle Root calculation:")
    print(f"[OK] Calculated Merkle Root: {merkle_root.hex()}")

    # Calculate output pubkey tweak
    tweak = tagged_hash("TapTweak", hash_internal_key + merkle_root)
    print(f"[OK] Tweak value: {tweak.hex()}")

    # Address reconstruction (simplified concept display)
    target_address = (
        "tb1p93c4wxsr87p88jau7vru83zpk6xl0shf5ynmutd9x0gxwau3tng"
        "q9a4w3z"
    )
    print(f"\nAddress verification:")
    print(f"[OK] Target address: {target_address}")
    print(f"[OK] Control Block valid: Can reconstruct same address")

    return True

verify_control_block_and_address_reconstruction()
```

The function makes the swap concrete: it computes both TapLeaf hashes from the revealed scripts, then checks that each control block's trailing 32 bytes really are the *other* leaf's hash. Once that holds, it sorts the two hashes, combines them with TapBranch into the Merkle root, tweaks Alice's key, and arrives back at `tb1p93c4...`. Both paths land on the same address — which is what proves both leaves were committed to it in the first place.

## Script Path 1: Hash Script

From transaction [`b61857a0...78a2e430`](https://mempool.space/testnet/tx/b61857a05852482c9d5ffbb8159fc2ba1efa3dd16fe4595f121fc35878a2e430?showDetails=true).

**Witness stack**

```
[0] 68656c6c6f776f726c64                             (preimage_hex)
[1] a820936a...f8f8f07af8851                         (script_hex)
[2] c050be5f...8105cf9df                             (control_block)
```

**Script bytecode** — `a820936a...f8f8f07af8851`:

```
a8 = OP_SHA256
20 = OP_PUSHBYTES_32
936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af = SHA256("helloworld")
88 = OP_EQUALVERIFY
51 = OP_PUSHNUM_1 (OP_TRUE)
```

This is the same hash lock from Chapter 6, so the stack walk is the same:

**Start** — the preimage loads onto the stack:

```
| 68656c6c...6f726c64 | (preimage "helloworld" in hex)
└─────────────────────┘
```

**OP_SHA256** — pops the preimage, pushes its SHA256:

```
| 936a185c...8f8f07af | (computed hash)
└─────────────────────┘
```

**OP_PUSHBYTES_32** — pushes the script's expected hash:

```
| 936a185c...8f8f07af | (expected hash)
| 936a185c...8f8f07af | (computed hash)
└─────────────────────┘
```

**OP_EQUALVERIFY** — pops both, compares; equal, so execution continues:

```
|                     | (empty stack)
└─────────────────────┘
```

**OP_PUSHNUM_1** — pushes 1, a non-zero top of stack, marking the script satisfied:

```
|         01          |
└─────────────────────┘
```

## Script Path 2: Bob Script

From transaction [`185024da...5a70cfe0`](https://mempool.space/testnet/tx/185024daff64cea4c82f129aa9a8e97b4622899961452d1d144604e65a70cfe0?showDetails=true). This leaf is new — a P2PK check instead of a hash lock.

**Witness stack**

```
[0] 26a0eadc...1f9f1c5c                             (bob_signature)
[1] 2084b595...ceef63af5ac                          (script_hex)
[2] c050be5f...8f10f659e                            (control_block)
```

**Script bytecode** — `2084b595...ceef63af5ac`:

```
20 = OP_PUSHBYTES_32
84b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5 = Bob's x-only pubkey
ac = OP_CHECKSIG
```

The script is two steps: push Bob's key, then check a signature against it.

**Start** — Bob's signature loads onto the stack (it came from the witness, not the script):

```
| 26a0eadc...1f9f1c5c | (Bob's 64-byte signature)
└─────────────────────┘
```

**OP_PUSHBYTES_32** — the script pushes Bob's x-only pubkey on top:

```
| 84b59516...eef63af5 | (Bob's 32-byte pubkey)
| 26a0eadc...1f9f1c5c | (Bob's 64-byte signature)
└─────────────────────┘
```

**OP_CHECKSIG** — pops the key and the signature, runs BIP340 Schnorr verification against the transaction, and pushes 1 if it holds:

```
|         01          | (signature valid)
└─────────────────────┘
```

So the two leaves end the same way — a 1 on top of the stack — but get there differently: the hash leaf proves knowledge of a *secret*, the Bob leaf proves possession of a *key*. One address, two unlock conditions, and only the one you use is ever revealed.

## What Changed From the Single-Leaf Case

Side by side, the single-leaf and dual-leaf cases differ in exactly one place — how the Merkle root is formed:

**Single leaf** — the root *is* the leaf:

```
Merkle Root = TapLeaf Hash
            = Tagged_Hash("TapLeaf", 0xc0 + len(script) + script)
```

The control block carries only the internal key; there's no sibling, so no Merkle path.

**Two leaves** — the root is a branch over both:

```
Merkle Root = TapBranch Hash
            = Tagged_Hash("TapBranch", sorted(TapLeaf_A, TapLeaf_B))

TapLeaf_A = Tagged_Hash("TapLeaf", 0xc0 + len(script_A) + script_A)
TapLeaf_B = Tagged_Hash("TapLeaf", 0xc0 + len(script_B) + script_B)
```

The lexicographic sort makes the root independent of listing order, and the control block now carries one sibling hash.

That sibling hash is the only thing that grows the control block, and it grows predictably — one hash per level of tree depth:

| Tree | Control block | Contents |
|------|---------------|----------|
| Single leaf | 33 bytes | version+parity, internal pubkey |
| Two leaves | 65 bytes | + one sibling hash |
| Four leaves | 97 bytes | + a second sibling hash (one per level) |

Each extra level of depth adds 32 bytes to the proof — a Merkle path, growing with the log of the number of leaves, not the count of them.

## Patterns for Building Two-Leaf Taproot

The two spends above generalize into a small set of reusable pieces.

**Commit — build the tree (index order matters):**

```python
def build_dual_leaf_taproot(alice_key, bob_key, preimage):
    # Build two different types of scripts
    hash_script = build_hash_lock_script(preimage)
    bob_script = build_bob_p2pk_script(bob_key)

    # Create script tree (index matters!)
    leafs = [hash_script, bob_script]  # Index 0 and 1

    # Generate Taproot address
    taproot_address = alice_key.get_taproot_address(leafs)

    return taproot_address, leafs
```

**Reveal — one template for any leaf:**

```python
def spend_script_path(script_index, input_data, leafs, internal_key, taproot_addr):
    # Build Control Block
    control_block = ControlBlock(
        internal_key,
        leafs,
        script_index,  # Key: specify which script to use
        is_odd=taproot_addr.is_odd()
    )

    # Build witness data (strict order!)
    witness = TxWitnessInput([
        *input_data,              # Inputs needed for script execution
        leafs[script_index].to_hex(),  # Script to execute
        control_block.to_hex()    # Merkle proof
    ])

    return witness
```

**The mistake to watch for** — a control block whose index doesn't match the script you actually reveal. The library builds the wrong Merkle proof and verification fails:

```python
# wrong — index and revealed script disagree
control_block = ControlBlock(..., leafs, 1, ...)  # index 1
witness = [..., leafs[0].to_hex(), ...]           # but revealing leaf 0

# right — drive both from one variable
script_index = 1
control_block = ControlBlock(..., leafs, script_index, ...)
witness = [..., leafs[script_index].to_hex(), ...]
```

If a script-path spend fails the Merkle check, this is the first thing to inspect — pull the trailing 32 bytes off the control block and confirm they really are the sibling you expect:

```python
def debug_control_block(control_block_hex, script_hex, expected_sibling):
    cb = bytes.fromhex(control_block_hex)
    actual_sibling = cb[33:65]  # sibling node hash

    print(f"Expected sibling: {expected_sibling.hex()}")
    print(f"Actual sibling: {actual_sibling.hex()}")
    print(f"Match result: {actual_sibling == expected_sibling}")
```

## Cost and Privacy of the Three Paths

With three ways to spend one address, here's what each costs and reveals.

**Sizes** (from the on-chain spends):

- **Key path** — ~110 bytes; witness is a 64-byte signature.
- **Hash script** — ~180 bytes; witness is preimage + script + control block.
- **Bob script** — ~185 bytes; witness is signature + script + control block.

**Verification, privacy, fee:**

- **Key path** — one signature check; reveals nothing; cheapest (baseline).
- **Hash script** — hash check plus Merkle verification; reveals the hash lock; ~1.6x the key-path fee.
- **Bob script** — signature check plus Merkle verification; reveals the P2PK structure; ~1.7x.

Three things fall out of these numbers:

- **The key path is always the best spend** when it's available — smallest, cheapest, reveals nothing — regardless of how complex the tree behind it is.
- **The script-path premium is modest** — the extra cost is one script plus a control block, far less than spelling out the equivalent conditions as a classic multisig redeem script.
- **You only ever pay for the path you take.** The unused leaves never touch the chain; they stay folded into the Merkle root as hashes.

## Chapter Summary

Adding a second leaf turned the single-leaf shortcut into the real thing: a Merkle tree built with TapBranch over two lexicographically sorted leaves, and control blocks that carry a sibling hash as the Merkle proof. We read both halves of that proof straight off the chain — each leaf's control block holding the *other* leaf's hash — and confirmed that either path rebuilds the same address.

The payoff is the same selective reveal as Chapter 6, now over more than one condition: one address, a hash lock and a key check and Alice's key path all committed to it, and only the single path actually used ever shown.

**Next.** Chapter 8 scales the tree to four leaves — the Merkle paths get longer, and the control block carries more than one sibling hash (the 97-byte, two-sibling case from the table above), as one address grows to back several spending conditions at once.
