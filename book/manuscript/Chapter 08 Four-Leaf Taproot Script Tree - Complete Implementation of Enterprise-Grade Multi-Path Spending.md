# Chapter 8: Four-Leaf Taproot Script Tree — Hashlock, Multisig, Timelock, and Signature

## From Two Leaves to Four

Chapter 7 built a two-leaf tree: one TapBranch over two leaves, and a control block carrying a single sibling hash. This chapter goes to four leaves, and that means a tree with two levels — leaves pair into branches, and the branches pair into the root. The control block grows to match: it now carries **two** sibling hashes (97 bytes), a Merkle path that climbs two levels instead of one.

Four leaves is also enough room to put genuinely different conditions side by side. The address we build has four script paths plus the key path — five ways to spend, one address:

1. **Hashlock** — anyone with the preimage "helloworld" can spend (the Chapter 6/7 hash lock).
2. **2-of-2 multisig** — Alice and Bob together, written with Tapscript's `OP_CHECKSIGADD`.
3. **CSV timelock** — Bob can spend, but only after 2 blocks have passed.
4. **Simple signature** — Bob can spend immediately.
5. **Key path** — Alice spends directly with her tweaked key; looks like an ordinary payment.

These map onto real patterns — a recovery path plus a timelock plus a cooperative close is the skeleton of a wallet-recovery scheme or a Lightning channel — but the point here is mechanical: how four leaves are committed, and how each path is revealed and verified.

## The Tree, and One Shared Address

Every spend below comes out of the same address:

```
Address: tb1pjfdm...jcr29q
```

Its tree is balanced — two leaves under each of two branches:

```
                 Merkle Root
                /            \
        Branch0              Branch1
        /      \             /      \
   Script0   Script1    Script2   Script3
  (Hashlock) (Multisig)  (CSV)    (Sig)
```

Each leaf's witness is the same shape we've used since Chapter 6 — data, then script, then control block — with the data part differing by what the script checks:

| Leaf | Unlocks with | Witness `[0..]` |
|------|--------------|-----------------|
| Script 0 Hashlock | the preimage | `[preimage]` |
| Script 1 Multisig | both signatures | `[bob_sig, alice_sig]` |
| Script 2 CSV | a signature, after 2 blocks | `[bob_sig]` + tx sequence set |
| Script 3 Simple sig | a signature | `[bob_sig]` |
| Key path | Alice's tweaked key | `[alice_sig]` |

## Building the Tree

The setup — keys, then four scripts, then the tree:

```python
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from bitcoinutils.script import Script
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput, Sequence
from bitcoinutils.utils import ControlBlock
from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK
import hashlib

# Set up testnet environment
setup('testnet')

# Generate participant keys
alice_priv = PrivateKey("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
bob_priv = PrivateKey("cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG")
alice_pub = alice_priv.get_public_key()
bob_pub = bob_priv.get_public_key()
```

The four scripts. Two are familiar from earlier chapters; two are new:

```python
# Script 0: SHA256 Hashlock
preimage = "helloworld"
hash0 = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
script0 = Script([
    'OP_SHA256',
    hash0,
    'OP_EQUALVERIFY',
    'OP_TRUE'
])

# Script 1: 2-of-2 Multisig (Tapscript style)
script1 = Script([
    "OP_0",                      # Initialize counter
    alice_pub.to_x_only_hex(),   # Alice's x-only public key
    "OP_CHECKSIGADD",           # Verify Alice signature, increment counter
    bob_pub.to_x_only_hex(),    # Bob's x-only public key
    "OP_CHECKSIGADD",           # Verify Bob signature, increment counter
    "OP_2",                     # Required signature count
    "OP_EQUAL"                  # Check counter == required count
])

# Script 2: CSV Timelock
relative_blocks = 2
seq = Sequence(TYPE_RELATIVE_TIMELOCK, relative_blocks)
script2 = Script([
    seq.for_script(),           # Push sequence value
    "OP_CHECKSEQUENCEVERIFY",   # Verify relative timelock
    "OP_DROP",                  # Clean stack
    bob_pub.to_x_only_hex(),    # Bob's public key
    "OP_CHECKSIG"               # Verify Bob's signature
])

# Script 3: Simple Signature
script3 = Script([
    bob_pub.to_x_only_hex(),
    "OP_CHECKSIG"
])
```

The tree is written as nested pairs — two leaves per branch — and that nesting is what gives a two-level Merkle structure:

```python
# Build script tree: [[left branch], [right branch]]
tree = [[script0, script1], [script2, script3]]

# Generate Taproot address using Alice's internal key
taproot_address = alice_pub.get_taproot_address(tree)
print(f"Taproot Address: {taproot_address.to_string()}")
# Output: tb1pjfdm...jcr29q
```

## Spending Each Path

The five spends differ only in what they put in the witness and which leaf index the control block points at. We'll walk all five; the patterns repeat.

### 1. Hashlock (Script 0)

The Chapter 6/7 hash lock, now at index 0 of a four-leaf tree — so its control block carries a two-level proof, but the call looks identical:

```python
def spend_hashlock_path():
    """Script 0: SHA256 Hashlock spending"""
    # UTXO information
    commit_txid = (
        "245563c5aa4c6d32fc34eed2f182b5ed"
        "76892d13370f067dc56f34616b66c468"
    )
    vout = 0
    input_amount = 1200  # satoshis
    output_amount = 666

    # Build transaction
    txin = TxInput(commit_txid, vout)
    txout = TxOutput(output_amount, alice_pub.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Key: Construct Control Block (script index 0)
    cb = ControlBlock(alice_pub, tree, 0, is_odd=taproot_address.is_odd())

    # Witness data: [preimage, script, control_block]
    preimage_hex = "helloworld".encode('utf-8').hex()
    tx.witnesses.append(TxWitnessInput([
        preimage_hex,           # Preimage to unlock hash lock
        script0.to_hex(),       # Executed script
        cb.to_hex()            # Merkle proof
    ]))

    return tx
# Testnet transaction ID: 1ba4835f...a6fd6845
```

### 2. Multisig (Script 1)

The multisig path is the new one worth dwelling on. Two signatures, both produced as script-path signatures over the same leaf:

```python
def spend_multisig_path():
    """Script 1: 2-of-2 Multisig spending"""
    # UTXO information
    commit_txid = (
        "1ed5a3e97a6d3bc0493acc2aac15011c"
        "d99000b52e932724766c3d277d76daac"
    )
    vout = 0
    input_amount = 1400
    output_amount = 668

    # Build transaction
    txin = TxInput(commit_txid, vout)
    txout = TxOutput(output_amount, alice_pub.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Key: Construct Control Block (script index 1)
    cb = ControlBlock(alice_pub, tree, 1, is_odd=taproot_address.is_odd())

    # Key: Script Path signature (note script_path=True)
    sig_alice = alice_priv.sign_taproot_input(
        tx, 0, [taproot_address.to_script_pub_key()], [input_amount],
        script_path=True,      # Script Path mode
        tapleaf_script=script1, # Specify leaf script
        tweak=False
    )

    sig_bob = bob_priv.sign_taproot_input(
        tx, 0, [taproot_address.to_script_pub_key()], [input_amount],
        script_path=True,
        tapleaf_script=script1,
        tweak=False
    )

    # Witness data: [Bob signature, Alice signature, script, control_block]
    # Note: Bob signature first (stack execution order)
    tx.witnesses.append(TxWitnessInput([
        sig_bob,               # Consumed second
        sig_alice,             # Consumed first
        script1.to_hex(),
        cb.to_hex()
    ]))

    return tx
# Testnet transaction ID: 1951a3be...b7e604a1
```

Both signers use `script_path=True`, `tapleaf_script=script1`, `tweak=False` — the same script-path signing from Chapter 7, just done twice over the one leaf. The witness order is the subtle part, and the stack walk below explains exactly why `sig_bob` goes first.

### 3. CSV timelock (Script 2)

The timelock path has one requirement the others don't: the *transaction* has to set a matching sequence, or `OP_CHECKSEQUENCEVERIFY` rejects it. The script says "2 blocks must have passed," and the input's sequence is what proves it:

```python
def spend_csv_timelock_path():
    """Script 2: CSV Timelock spending"""
    # UTXO information
    commit_txid = (
        "9a2bff4161411f25675c730777c7b4f5"
        "b2837e19898500628f2010c1610ac345"
    )
    vout = 0
    input_amount = 1600
    output_amount = 800

    # Key: CSV requires special sequence value
    relative_blocks = 2
    seq = Sequence(TYPE_RELATIVE_TIMELOCK, relative_blocks)
    seq_for_input = seq.for_input_sequence()

    # Build transaction (note sequence parameter)
    txin = TxInput(commit_txid, vout, sequence=seq_for_input)  # Key!
    txout = TxOutput(output_amount, alice_pub.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Control Block (script index 2)
    cb = ControlBlock(alice_pub, tree, 2, is_odd=taproot_address.is_odd())

    # Bob signature
    sig_bob = bob_priv.sign_taproot_input(
        tx, 0, [taproot_address.to_script_pub_key()], [input_amount],
        script_path=True,
        tapleaf_script=script2,
        tweak=False
    )

    # Witness data: [Bob signature, script, control_block]
    tx.witnesses.append(TxWitnessInput([
        sig_bob,
        script2.to_hex(),
        cb.to_hex()
    ]))

    return tx
# Testnet transaction ID: 98361ab2...d17f41ee
```

Note the symmetry: the script carries `seq.for_script()` (the timelock condition), and the input carries `seq.for_input_sequence()` (the claim that it's satisfied). Both come from the same `Sequence` object, and both have to be present — the script states the rule, the transaction supplies the evidence.

### 4. Simple signature (Script 3)

The plainest leaf — Bob signs, no extra conditions. Same as Chapter 7's Bob script, now at index 3:

```python
def spend_simple_sig_path():
    """Script 3: Simple Signature spending"""
    # UTXO information
    commit_txid = (
        "632743eb43aa68fb1c486bff48e8b27c"
        "436ac1f0d674265431ba8c1598e2aeea"
    )
    vout = 0
    input_amount = 1800
    output_amount = 866

    # Build transaction
    txin = TxInput(commit_txid, vout)
    txout = TxOutput(output_amount, alice_pub.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Control Block (script index 3)
    cb = ControlBlock(alice_pub, tree, 3, is_odd=taproot_address.is_odd())

    # Bob signature
    sig_bob = bob_priv.sign_taproot_input(
        tx, 0, [taproot_address.to_script_pub_key()], [input_amount],
        script_path=True,
        tapleaf_script=script3,
        tweak=False
    )

    # Witness data: [Bob signature, script, control_block]
    tx.witnesses.append(TxWitnessInput([
        sig_bob,
        script3.to_hex(),
        cb.to_hex()
    ]))

    return tx
# Testnet transaction ID: 1af46d4c...4c6c71b9
```

### 5. Key path

And the one that reveals nothing — Alice's key-path spend, identical in spirit to Chapter 6's. It still needs the whole `tree` to rebuild the tweak, but nothing about the tree reaches the chain:

```python
def spend_key_path():
    """Key Path: Most efficient and private spending method"""
    # UTXO information
    commit_txid = (
        "42a9796a91cf971093b35685db9cb1a1"
        "64fb5402aa7e2541ea7693acc1923059"
    )
    vout = 0
    input_amount = 2000
    output_amount = 888

    # Build transaction
    txin = TxInput(commit_txid, vout)
    txout = TxOutput(output_amount, alice_pub.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Key: Key Path signature (note script_path=False)
    sig_alice = alice_priv.sign_taproot_input(
        tx, 0, [taproot_address.to_script_pub_key()], [input_amount],
        script_path=False,      # Key Path mode
        tapleaf_scripts=tree    # Complete script tree (for tweak calculation)
    )

    # Witness data: Only one signature (most efficient!)
    tx.witnesses.append(TxWitnessInput([sig_alice]))

    return tx
# Testnet transaction ID: 1e518aa5...e95600da
```

Note the parameter difference one more time, since it's the single most common point of confusion: the key path passes `tapleaf_scripts=tree` (plural, the whole tree, to compute the tweak) with `script_path=False`; every script path passes `tapleaf_script=script_n` (singular, one leaf) with `script_path=True`.

## How OP_CHECKSIGADD Runs

The multisig leaf is the one new piece of script execution in this chapter, so let's walk its stack. Tapscript replaced the old `OP_CHECKMULTISIG` with `OP_CHECKSIGADD`, which keeps a running count of valid signatures:

```python
# Script 1: 2-of-2 multisig (tapscript style)
script1 = Script([
    "OP_0",                      # Initialize counter to 0
    alice_pub.to_x_only_hex(),   # Alice's x-only public key
    "OP_CHECKSIGADD",           # Verify Alice signature, increment counter if successful
    bob_pub.to_x_only_hex(),    # Bob's x-only public key
    "OP_CHECKSIGADD",           # Verify Bob signature, increment counter if successful
    "OP_2",                     # Push required signature count 2
    "OP_EQUAL"                  # Check if counter equals required count
])
```

The witness puts both signatures on the stack before the script runs, and the order matters:

```python
# Witness data: [Bob signature, Alice signature, script, control_block]
# Note: Bob signature first, but consumed second!
tx.witnesses.append(TxWitnessInput([
    sig_bob,               # Stack position: lower, consumed second by OP_CHECKSIGADD
    sig_alice,             # Stack position: top, consumed first by OP_CHECKSIGADD
    script1.to_hex(),
    cb.to_hex()
]))
```

**Stack walk** — script `OP_0 [Alice_PubKey] OP_CHECKSIGADD [Bob_PubKey] OP_CHECKSIGADD OP_2 OP_EQUAL`.

**Start** — both signatures loaded, `sig_alice` on top:

```
| sig_alice   | <- top, consumed first
| sig_bob     |
└─────────────┘
```

**OP_0** — pushes the counter, initialized to 0:

```
| 0           | <- counter
| sig_alice   |
| sig_bob     |
└─────────────┘
```

**[Alice_PubKey]** — the script pushes Alice's key:

```
| alice_pubkey|
| 0           |
| sig_alice   |
| sig_bob     |
└─────────────┘
```

**OP_CHECKSIGADD** — pops the key, pops the counter, pops the signature below it; verifies `sig_alice` against `alice_pubkey`; pushes counter+1:

```
| 1           | <- counter is now 1
| sig_bob     |
└─────────────┘
```

**[Bob_PubKey]** then **OP_CHECKSIGADD** — same again for Bob, consuming `sig_bob`:

```
| 2           | <- counter is now 2
└─────────────┘
```

**OP_2** then **OP_EQUAL** — push the required count, compare; `2 == 2`, so push 1 and the script is satisfied:

```
| 1           |
└─────────────┘
```

That's why `sig_alice` has to be on top of `sig_bob` in the witness: the *first* `OP_CHECKSIGADD` is Alice's, and it consumes whichever signature is on top at that moment. The witness lists `[sig_bob, sig_alice]` — bob first, so alice ends up on top, so alice is checked first. Reverse them and both checks fail.

```python
# wrong order — both checks fail
witness = [sig_alice, sig_bob, script1.to_hex(), cb.to_hex()]

# right order — bob first, alice ends up on top
witness = [sig_bob, sig_alice, script1.to_hex(), cb.to_hex()]
```

**Why `OP_CHECKSIGADD` and not `OP_CHECKMULTISIG`?** Three concrete reasons:
- It checks one signature at a time and stops on failure, instead of trying combinations.
- The counter is explicit — no off-by-one `OP_CHECKMULTISIG` dummy-element quirk.
- It takes 32-byte x-only keys directly, where `OP_CHECKMULTISIG` wanted 33-byte compressed keys.

## The Four-Leaf Control Block

With two levels in the tree, each leaf's Merkle proof is two hashes — its immediate sibling, then that pair's sibling branch — so the control block is 97 bytes:

```
33 bytes: version+parity (1) + internal pubkey (32)
+32 bytes: sibling leaf hash    (level 1)
+32 bytes: sibling branch hash  (level 2)
= 97 bytes
```

Which two hashes each leaf needs depends on where it sits:

```python
paths = {
    0: "[Script1_TapLeaf, Branch1_TapBranch]",  # Hashlock
    1: "[Script0_TapLeaf, Branch1_TapBranch]",  # Multisig
    2: "[Script3_TapLeaf, Branch0_TapBranch]",  # CSV
    3: "[Script2_TapLeaf, Branch0_TapBranch]"   # Simple Sig
}
```

### Reading a real control block

Take the multisig spend, [`1951a3be...b7e604a1`](https://mempool.space/testnet/tx/1951a3be0f05df377b1789223f6da66ed39c781aaf39ace0bf98c3beb7e604a1?showDetails=true), and pull its witness off the chain:

```python
def analyze_real_multisig_transaction():
    """Analyze Control Block verification of real multisig transaction"""

    # Witness stack extracted from on-chain data
    witness_stack = [
        # Bob's signature (first witness item)
        (
            "31fa0ca7929dac01b908349326183dd7a0f752475d42f11dc2cd0075110ca2a4"
            "c255f3e310dfc0800e69609c872254241dcf827847e5b64821cefa6c6db575bc"
        ),

        # Alice's signature (second witness item)
        (
            "22272de665b998668ae9e97cb72d9814d362ae101ee878caee04da0d2a7efb14"
            "e8bcdd7eb8082fad30864ec7f22bce6fb2d2178764a0b2f5427346e4b5821fa0"
        ),

        # Multisig script (third witness item)
        (
            "002050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb"
            "4d3ba2084b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef"
            "63af5ba5287"
        ),

        # Control Block (fourth witness item) - 97 bytes
        (
            "c050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3"
            "fe78d8523ce9603014b28739a51ef826f791aa17511e617af6dc96a8f10f659eda"
            "55197526f26fa309563b7a3551ca945c046e5b7ada957e59160d4d27f299e3"
        )
    ]

    print("=== On-Chain Multisig Transaction Control Block Analysis ===")
    return witness_stack
```

Splitting the 97-byte control block into its four parts:

```python
def parse_control_block_bytes():
    """Parse detailed structure of 97-byte Control Block"""

    cb_hex = (
        "c050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3"
        "fe78d8523ce9603014b28739a51ef826f791aa17511e617af6dc96a8f10f659eda"
        "55197526f26fa309563b7a3551ca945c046e5b7ada957e59160d4d27f299e3"
    )
    cb_bytes = bytes.fromhex(cb_hex)

    # Byte 0: Version + parity bit
    version_and_parity = cb_bytes[0]  # 0xc0
    leaf_version = version_and_parity & 0xfe  # 0xc0 (leaf version)
    parity_bit = version_and_parity & 0x01    # 0 (even)

    # Bytes 1-32: Internal public key (Alice's x-only public key)
    internal_pubkey = cb_bytes[1:33].hex()

    # Bytes 33-64: First sibling node (Script 0's TapLeaf hash)
    sibling_1 = cb_bytes[33:65].hex()

    # Bytes 65-96: Second sibling node (Branch 1's TapBranch hash)
    sibling_2 = cb_bytes[65:97].hex()

    print("Control Block Detailed Parsing:")
    print(f"Total length: {len(cb_bytes)} bytes")
    print(f"Leaf version: 0x{leaf_version:02x}")
    print(f"Parity bit: {parity_bit} (output key is {'odd' if parity_bit else 'even'})")
    print(f"Internal pubkey: {internal_pubkey}")
    print(f"  -> Alice's x-only public key")
    print(f"Sibling node 1: {sibling_1}")
    print(f"  -> Script 0 (Hashlock) TapLeaf hash")
    print(f"Sibling node 2: {sibling_2}")
    print(f"  -> Branch 1 (Script2+Script3) TapBranch hash")

    return {
        'leaf_version': leaf_version,
        'parity_bit': parity_bit,
        'internal_pubkey': internal_pubkey,
        'sibling_1': sibling_1,
        'sibling_2': sibling_2
    }
```

### Climbing the two levels back to the address

With the script and its two sibling hashes in hand, verification is the same idea as Chapter 7 — recompute the root and check it rebuilds the address — but now it takes two TapBranch steps instead of one. The code below reuses `tagged_hash`, the BIP-341 tagged-hash helper introduced in Chapter 7 (`tagged_hash(tag, msg) = SHA256(SHA256(tag) || SHA256(tag) || msg)`); bring it into scope before running this block:

```python
def reconstruct_merkle_root_step_by_step():
    """Step-by-step Merkle Root reconstruction for Control Block verification"""

    # Parsed CB data
    cb_data = parse_control_block_bytes()

    # Step 1: Calculate Script 1 (Multisig) TapLeaf hash
    multisig_script_hex = (
        "002050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb"
        "4d3ba2084b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef"
        "63af5ba5287"
    )
    script_bytes = bytes.fromhex(multisig_script_hex)

    # TapLeaf = Tagged_Hash("TapLeaf", version + length + script)
    tapleaf_data = bytes([cb_data['leaf_version']]) + len(script_bytes).to_bytes(1, 'big') + script_bytes
    script1_tapleaf = tagged_hash("TapLeaf", tapleaf_data)
    print("Step 1: current script's TapLeaf hash")
    print(f"  Script1 TapLeaf: {script1_tapleaf.hex()}")

    # Step 2: Combine with Script 0 (sibling 1) to form Branch 0
    script0_tapleaf = bytes.fromhex(cb_data['sibling_1'])
    if script0_tapleaf < script1_tapleaf:           # lexicographic order
        branch0_data = script0_tapleaf + script1_tapleaf
    else:
        branch0_data = script1_tapleaf + script0_tapleaf
    branch0_hash = tagged_hash("TapBranch", branch0_data)
    print("Step 2: Branch0 = TapBranch(Script0, Script1)")
    print(f"  Branch0: {branch0_hash.hex()}")

    # Step 3: Combine with Branch 1 (sibling 2) to form the Merkle Root
    branch1_hash = bytes.fromhex(cb_data['sibling_2'])
    if branch0_hash < branch1_hash:
        root_data = branch0_hash + branch1_hash
    else:
        root_data = branch1_hash + branch0_hash
    merkle_root = tagged_hash("TapBranch", root_data)
    print("Step 3: MerkleRoot = TapBranch(Branch0, Branch1)")
    print(f"  Merkle Root: {merkle_root.hex()}")

    # Step 4: Tweak the internal key with the Merkle root
    internal_pubkey = bytes.fromhex(cb_data['internal_pubkey'])
    tap_tweak = tagged_hash("TapTweak", internal_pubkey + merkle_root)
    print("Step 4: TapTweak(internal_pubkey || merkle_root)")
    print(f"  Tweak: {tap_tweak.hex()}")

    # Step 5: Output key = internal_pubkey + tap_tweak * G  (needs an EC library),
    #         then bech32m-encode as the P2TR address. The library does this; the
    #         check is simply that it rebuilds the funding address:
    expected_address = (
        "tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqj"
        "cr29q"
    )
    print("Step 5: output key -> address")
    print(f"  Expected address: {expected_address}")
    print(f"  Control Block valid: rebuilds the funding address")

    return tap_tweak

# Execute complete verification
if __name__ == "__main__":
    analyze_real_multisig_transaction()
    parse_control_block_bytes()
    reconstruct_merkle_root_step_by_step()
```

Running it against the real bytes gives Script1 TapLeaf `63cb9e47...`, Branch0 `d6ac4c01...`, Merkle root `33fd4d4b...`, and a tweak that rebuilds `tb1pjfdm...jcr29q` — the same address all five spends came out of. Two things fall out of the parse worth noticing:

- Sibling 1 is `fe78d852...f10f659e` — exactly Script 0's TapLeaf hash, and the very same value we computed for the hash lock back in Chapter 7. Same script, same leaf hash, across chapters.
- The proof is hierarchical: level 0 is the multisig leaf itself, level 1 is `Branch0 = TapBranch(Script0, Script1)`, level 2 is `Root = TapBranch(Branch0, Branch1)`. Every TapBranch sorts its two inputs lexicographically, which is what makes the root reproducible by anyone.

## Three Things That Bite

The four-leaf spends fail in a few predictable ways. In order of how often they catch people:

**Witness order, for multisig.** Bob's signature goes first in the list so Alice's ends up on top of the stack — the reverse fails both checks (see the stack walk above):

```python
# wrong
witness = [sig_alice, sig_bob, script, control_block]
# right
witness = [sig_bob, sig_alice, script, control_block]
```

**Sequence, for CSV.** A CSV script only passes if the input's sequence says enough blocks have elapsed. Forget it and `OP_CHECKSEQUENCEVERIFY` rejects the spend:

```python
# wrong — default sequence, CSV fails
txin = TxInput(txid, vout)
# right — sequence matches the script's timelock
txin = TxInput(txid, vout, sequence=seq.for_input_sequence())
```

**Key path vs script path signing.** The two take different parameters; mixing them up is the most common single mistake:

```python
# key path:    whole tree (to tweak the key), script_path=False
sig = priv.sign_taproot_input(..., script_path=False, tapleaf_scripts=tree)
# script path: one leaf, script_path=True
sig = priv.sign_taproot_input(..., script_path=True, tapleaf_script=script)
```

## Chapter Summary

Four leaves turned the single TapBranch of Chapter 7 into a two-level tree, and the control block grew to match — 97 bytes carrying a two-hash Merkle path. We put four genuinely different conditions under one address (a hash lock, a 2-of-2 multisig, a CSV timelock, and a plain signature), spent each one on testnet, and verified the multisig's control block by climbing both branch levels back to the same funding address every path shares.

Two ideas are the ones to keep:

- **`OP_CHECKSIGADD`** is how Tapscript does multisig — a running counter of valid signatures, fed by a witness whose signature order has to match the order the script checks them.
- **A taller tree means a longer Merkle path.** Each level of depth adds one 32-byte sibling to the control block; the cost grows with the log of the number of leaves, not the count.

### What Chapters 5–8 covered

This chapter completes the foundational part of the book. Since Chapter 5, the four chapters have built up Taproot one mechanism at a time:

- **Chapter 5** — Schnorr signatures and the key tweak: how one public key can commit to extra data.
- **Chapter 6** — a single-leaf script path: commit one script, then spend it or use the key path.
- **Chapter 7** — two leaves: a Merkle root over a TapBranch, and a control block that proves a leaf with its sibling.
- **Chapter 8** — four leaves and a two-level tree, with multisig, a timelock, and a 97-byte proof.

These four build directly on each other: the key tweak from Chapter 5 is what commits the Merkle root, the commit–reveal pattern from Chapter 6 is how every script path works, and the Merkle proof grows by one sibling hash per level from Chapter 7 to Chapter 8. If those connections aren't clear yet, it's worth reading the four chapters together before moving on — the rest of the book assumes them.

### Chapters 9–12: applications

The second half of the book moves from how Taproot works to how it is used. Each chapter takes a real system and points out where these mechanisms appear:

- **Chapter 9 — Ordinals and BRC-20.** Using a script path to store data instead of spending conditions: a single-leaf script that commits arbitrary content into a Taproot output.
- **Chapter 10 — RGB and Tapret.** Client-side validation, with commitments placed inside the script tree.
- **Chapter 11 — Lightning channels.** Moving channels from P2WSH multisig to Taproot, and the privacy this adds.
- **Chapter 12 — Silent Payments.** The elliptic-curve arithmetic from Chapter 5 again, this time for address privacy: reusable addresses that leave no link on chain.

**Next.** Chapter 9 starts with a single leaf, like Chapter 6, but uses it for something different: storing data in a Taproot output.
