# Chapter 10: RGB and Tapret — Commitments Inside the Script Tree

## What RGB Is

RGB is a smart contract protocol built on top of Bitcoin. Contract state is maintained off-chain and verified by participants themselves (client-side verification); Bitcoin's role is singular — through the spending order of UTXOs, it ensures state transitions are irreversible and cannot be double-spent. Taproot serves as the commitment carrier: with each state transition, RGB embeds a cryptographic commitment inside the script tree of a Taproot output, leaving no readable information on-chain.

---

## The Opposite of Ordinals: Nothing Visible On-Chain

Chapter 9's Ordinals put data into the witness. The VM skips it, the indexer reads it. On-chain there are bytes, structure, decodable content.

RGB does the opposite: nothing is visible on-chain.

The same Taproot transaction, two ordinary P2TR outputs. `getrawtransaction` returns `OP_1 + 32 bytes`, indistinguishable from any key-path spend. The RGB state commitment is hidden inside the script tree. Bitcoin consensus does not execute it, does not interpret it, does not know it exists. Verification happens entirely on the client.

This is the dividing line between Chapter 9 and Chapter 10: one stores data on-chain, the other stores a commitment.

---

## Tapret: An Unspendable Leaf at Depth 1 of the Script Tree

RGB supports two commitment schemes. Opret places the commitment in an OP_RETURN transaction output — 34 bytes, visible on-chain (in this chapter **MPC** stands for **Multi-Protocol Commitments**, not the cryptographic Multi-Party Computation sharing the same abbreviation):

```
Opret (transaction output):
  scriptPubKey: OP_RETURN OP_PUSHBYTES_32 <32-byte MPC commitment>
  value: 0 sats
```

Tapret is different — the commitment is not placed in an output, but inside a leaf node of the Taproot script tree:

```
Tapret leaf script (64 bytes, leaf version 0xC0):
  50 50 ... 50              ← 29 bytes OP_RESERVED (0x50)
  6A                        ← OP_RETURN
  21                        ← OP_PUSHBYTES_33
  <32-byte MPC commitment>
  <1-byte nonce>
```

The OP_RETURN inside the leaf terminates script execution immediately and fails, making it permanently unspendable. But this leaf is not a transaction output — it lives inside the script tree, invisible from the outside.¹

**Insertion position** (LNPBP-12 specification): depth 1, placed at the rightmost position in BIP-341 lexicographic order. Depth 0 is the Merkle root; depth 1 is the root's direct children. The existing script becomes the left sibling at depth 1; Tapret is inserted as the right sibling at depth 1.

For a single existing script Script_A:

```
Before:                        After:

      P                               P'   ← different tweaked key
      |                               |
  merkle_root                    merkle_root'
      |                           /           \
   Script_A               Script_A         Tapret_Leaf
  (depth 0, only leaf)    (depth 1)        (depth 1, rightmost)
                                        unspendable, contains MPC commitment
```

The Merkle root changes, the output key changes with it, but the on-chain appearance remains a standard P2TR address. The RGB client fetches the txid, locates the output, finds the Tapret leaf at the rightmost position of depth 1 per the specification, extracts the MPC commitment, and verifies the state transition.

The name `tapret1st` comes from LNPBP-12: `tapret` is the commitment scheme name, `1st` corresponds to depth 1 (counting from 0, where the root is 0).

---

## Seals: Binding State to a UTXO

RGB uses single-use seals to bind state to a specific UTXO. A seal points to a particular transaction output (txid:vout). When that UTXO is spent, the seal closes and the state transition is complete and irreversible. New seals open on the outputs of the new transaction, carrying the next state forward. The seal mechanism works like this: whoever holds the UTXO holds the state — Bitcoin's double-spend protection becomes RGB's double-spend protection.

---

## On-Chain Example: Testnet Transfer Transaction

The following experiment runs on Bitcoin testnet — Alice transfers 100 units of an RGB20 asset to Bob.

**Transfer transaction**: [64a14551...35c20b6b](https://mempool.space/testnet/tx/64a1455125724ce79d4914d7af5e0226f465c7522b8dd6f048440b8935c20b6b?showDetails=true)

On mempool.space:

- vout:0: `tb1pd057tgt4u38ur4znyszme79l...jq02w5v`, V1_P2TR
- vout:1: `tb1p9yjaffzhuh9p7d9gnwfunxssn...hqellhrw`, V1_P2TR

Both outputs are standard P2TR. No RGB trace on-chain. Run `code/chapter10/02_verify_tx_onchain.py` to verify directly:

```bash
python3 02_verify_tx_onchain.py 64a1455125724ce79d4914d7af5e0226f465c7522b8dd6f048440b8935c20b6b
```

Output:

```
vout[0]  type=v1_p2tr  value=600 sats   tb1pd057...
vout[1]  type=v1_p2tr  value=2000 sats  tb1p9yja...

All outputs are P2TR. No OP_RETURN. Indistinguishable from a normal Taproot spend.
```

**Bob's state after the transfer** (RGB client output):

```
Owned:
  State         Seal                                                   Witness
  assetOwner:
          100   bc:tapret1st:64a14551...c20b6b:1   bc:64a14551...c20b6b
                                                   (bitcoin:4909164, 2026-04-04 03:49:34)
```

Field-by-field breakdown:

| Field | Value | Meaning |
|-------|-------|---------|
| `100` | 100 | Bob's current asset balance |
| `bc:tapret1st:` | prefix | Commitment scheme: Bitcoin testnet, Tapret, depth 1 |
| `64a14551...c20b6b:1` | txid:vout | Commitment anchored to vout:1 of this transaction |
| `bc:64a14551...c20b6b` | witness | On-chain anchor txid |
| `bitcoin:4909164` | block height | Height at which the transaction was confirmed |

The seal `tapret1st:64a14551...c20b6b:1` points to vout:1 visible on mempool — a standard P2TR output. The Tapret leaf inside the script tree does not appear on mempool; it exists in the RGB client's consignment data.

**Seal lifecycle**

Genesis seal (closed):

```
22d13f86...5d2a:0  ->  1,000,000 units  ->  spent
```

This transfer opens two new seals, both anchored to the same transaction:

```
Transfer transaction: 64a14551...c20b6b
  vout:0  ->  tapret1st:...:0  ->  999,900 (Alice's change)
  vout:1  ->  tapret1st:...:1  ->  100     (Bob's receipt)

Conservation check: 999,900 + 100 = 1,000,000 [OK]
```

The old seal closes; the new transaction opens two new seals, each corresponding to a P2TR output whose script tree hides a Tapret commitment.

---

## Code: Six-Step Transfer Flow

This chapter's experiment depends on the RGB CLI and an Esplora indexer. Environment setup is in `code/chapter10/README.md`. Below is the core calling pattern.

`01_rgb_transfer_single_hop.py` breaks the transfer into six steps, each mapping to a phase in the chapter:

```python
def _rgb(wallet_dir: str, *args: str) -> str:
    """Call the rgb CLI and return stdout."""
    cmd = [rgb_bin, "-d", wallet_dir, "-n", network,
           *args, "--sync", f"--esplora={esplora}"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.stdout
```

Each step calls the CLI through this wrapper. `--sync` ensures the wallet state is synchronized with the chain before every operation.

**Bob's complete output after transfer**:

```
Global:
  spec := ticker "TNW022", name "Testnet Workflow Asset", ...
  issuedSupply := 1000000

Owned:
  State         Seal                                                                            Witness
  assetOwner:
          100   bc:tapret1st:64a1455125724ce79d4914d7af5e0226f465c7522b8dd6f048440b8935c20b6b:1
                bc:64a1455125724ce79d4914d7af5e0226f465c7522b8dd6f048440b8935c20b6b
                (bitcoin:4909164, 2026-04-04 03:49:34)
```

**Alice's complete state (`-a` flag)**:

```
Owned:
  State         Seal                                                   Witness
  assetOwner:
       999900   bc:tapret1st:64a14551...c20b6b:0  ...  -- third-party
          100   bc:tapret1st:64a14551...c20b6b:1  ...  -- third-party
      1000000   bc:tapret1st:22d13f86...5d2a:0    ~    -- spent
```

`third-party` is not an error. The state transition is valid at the protocol level, amounts are conserved, and Bob correctly received 100. `third-party` is a wallet descriptor scope issue: the client can see these seals exist, but cannot identify them as Alice's currently spendable state. This is a property of the client view layer, not an RGB protocol problem.

---

## What Bitcoin Sees vs What the RGB Client Sees

```
On-chain (visible to anyone):
  tx 64a14551...c20b6b
  ├── vout:0  ->  P2TR address tb1pd057...  (600 sats)
  └── vout:1  ->  P2TR address tb1p9yja...  (2,000 sats)
  No OP_RETURN output. No RGB marker of any kind.

RGB client (requires consignment to parse):
  vout:0 script tree, depth 1: Tapret leaf
    -> MPC commitment -> Alice's change, 999,900 units
  vout:1 script tree, depth 1: Tapret leaf
    -> MPC commitment -> Bob's receipt, 100 units
```

Bitcoin consensus validates the signature and transaction format. The Tapret leaf sits inside the script tree, is never executed, and has no effect on consensus. An external observer cannot distinguish this transaction from an ordinary Taproot transfer.

Comparison with Chapter 9:

| | Ordinals/BRC-20 | RGB/Tapret |
|---|---|---|
| Commitment location | Witness (visible after reveal) | Script tree leaf (never visible) |
| On-chain data | Present (JSON in witness) | None |
| Verifier | Off-chain indexer | RGB client, client-side verification |
| Trust model | Depends on indexer consensus | Client verifies independently |

---

## How Tapret Changes the Output Key

Inserting a Tapret leaf into the script tree changes the Merkle root, which feeds directly into the Chapter 5 formula:

```
t = HashTapTweak(internal_key || merkle_root)
Q = internal_key + t * G
```

The output key `Q` is the on-chain Taproot address. The tweak `t` now encodes an RGB state commitment rather than a spending condition, but `Q` is indistinguishable from any other Taproot key. There is no way to tell whether a tweak came from a spendable script tree or an unspendable Tapret leaf.

`code/chapter10/03_tapret_leaf.py` constructs the 64-byte leaf in pure Python and prints the structure byte by byte — no RGB CLI required, anyone can run it.

**Effect on wallet identification:** The output's owner must store the tweak value alongside the HD derivation path. Without it, the wallet cannot recompute `Q` from the internal key and cannot recognize that output as its own. In RGB wallet implementations, these tweaks are stored in a mapping (`descriptor.toml`) keyed by the HD terminal path (for example `&10/19`). If this mapping is lost, outputs appear as third-party — the funds are not gone (the private key still exists) but the wallet cannot identify them.

This is a general Taproot property, not specific to RGB: any protocol that inserts non-standard leaves into the script tree must persist the tweak-to-key mapping for the output owner to maintain spendability.

---

## Chapter Summary

RGB uses Tapret to hide state commitments inside the Taproot script tree at depth 1. The OP_RETURN inside the leaf terminates script execution immediately and fails, making the leaf permanently unspendable; it has a fixed length of 64 bytes and its position is specified by the LNPBP-12 standard. The on-chain output is a standard P2TR address; the Tapret leaf changes the Merkle root and output key as part of the script tree, but is invisible to external observers.

A seal is the binding point between RGB state and a specific UTXO. When a UTXO is spent the old seal closes; the new transaction opens new seals on its outputs — one for change, one for the recipient. Amount conservation is verified by the RGB client from consignment data, with no indexer involved.

Tapret exploits the Merkle commitment structure of the Taproot script tree — no script is executed, no path is spent. A leaf is inserted into the tree, and the output key silently carries a state anchor invisible to any external observer. RGB introduces no new transaction format and changes no consensus rules; it relies on a property already present in BIP-341: the script tree determines the output key.

The next chapter covers Taproot channels in the Lightning Network: also Taproot outputs, but with a completely different commitment structure and update mechanism — channel state is held symmetrically off-chain and only surfaces on-chain in the event of a dispute.

---

¹ The Tapret leaf structure in this chapter follows the current RGB implementation (rgb-wallet 0.11.0-beta.9), verified against PSBT output on testnet and consistent with [RGB Docs: Tapret](https://docs.rgb.info/commitment-layer/deterministic-bitcoin-commitments-dbc/tapret). The original LNPBP-12 draft describes a slightly different byte layout; both produce a 64-byte unspendable leaf. If you are using a different RGB version, decode your own PSBT output to verify the actual structure — details and the comparison are in `code/chapter10/README.md`.