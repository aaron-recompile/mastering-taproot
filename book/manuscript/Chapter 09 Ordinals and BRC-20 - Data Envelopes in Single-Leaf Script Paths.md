# Chapter 9: Ordinals and BRC-20 — Data Envelopes in Single-Leaf Script Paths

## A Single Leaf That Carries Data

Ordinals and BRC-20 generated significant attention in 2023, and a large volume of related transactions exist on mainnet. If you look at their on-chain structure, they turn out to be surprisingly simple: a single-leaf Taproot script path, one commit transaction, one reveal transaction.

The previous eight chapters moved from single-leaf to four-leaf, with increasingly complex script trees. Ordinals steps back to a single leaf — not because it is simpler, but because the purpose is different. The script in the leaf is not there to execute a condition; it is there to carry data. The VM skips the data segment, the data stays in the witness, and an off-chain indexer reads it.

We can take it apart with the same commit–reveal mechanics from the Taproot chapters — only here the revealed leaf carries data instead of a spending condition.

---

## The Data Envelope: `OP_0 OP_IF ... OP_ENDIF`

An Ordinals leaf script looks like this:

```
<pubkey> OP_CHECKSIG
OP_0
OP_IF
  <"ord">
  OP_1
  <content-type>
  OP_0
  <data>
OP_ENDIF
```

VM execution path:

```
  <pubkey> OP_CHECKSIG  ← signature verified, executed
  OP_0                  ← false pushed onto stack, executed
  OP_IF                 ← condition false, jump to OP_ENDIF
  ┌──────────────────────────────────────┐
  │  "ord"                               │
  │  content-type                        │  ← VM skips
  │  JSON payload                        │     indexer reads here
  └──────────────────────────────────────┘
  OP_ENDIF              ← execution resumes
```

The bytes the VM skips are still in the witness, committed on-chain with the reveal transaction and immutable thereafter. Bitcoin consensus validates the signature and script format; it does not interpret data. An off-chain indexer can scan the witness and compute token state according to its protocol rules (see the on-chain example below for the specific JSON format).

BRC-20 uses the same structure, but specifies conventions for the JSON fields (`p` / `op` / `tick` / `amt`).

---

## On-Chain Example: Testnet BRC-20 Mint Transaction Pair

The following two testnet transactions are the basis for this section's analysis:

**Commit**: [515ddcfc...1f950aa0](https://mempool.space/testnet/tx/515ddcfc2ddb5ebadb6be493a955e490c54d399cf2cc528cecc302e41f950aa0?showDetails=true)

| Field | Value |
|---|---|
| Input | 2,400 sats, key-path address |
| Output 0 | 1,046 sats -> `tb1pe7dahu72...seqqfsp` (temporary address) |
| Output 1 | 1,054 sats -> change |
| Fee | 300 sats |
| Witness | Single Schnorr signature (key path) |

The inscription content is indirectly committed into the output public key via the Taproot tweak; no JSON is visible on-chain.

**Reveal**: [2fc169a5...fff57547](https://mempool.space/testnet/tx/2fc169a5eb2f096bc8e64cb946380869ee2a2099f67cc3d5e719fbe9fff57547?showDetails=true)

| Field | Value |
|---|---|
| Input | 1,046 sats, from temporary address |
| Output | 546 sats -> destination address |
| Fee | 500 sats |
| Witness | Signature, inscription script, control block |

The three witness elements of the reveal:

```
Signature (continuous hex, line-wrapped for display):
894bf65e9593b1ce18071d44325add446b91e4638271318f1980d432e5de88f
b743fcf7c69a5a3e98ffe0306944ddc1e4ab38e4c525fb1e0846263183a6de375

Script:
2050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3ac
0063036f726451
18746578742f706c61696e3b636861727365743d7574662d38
00
357b2270223a226272632d3230222c226f70223a226d696e74222c
227469636b223a2244454d4f222c22616d74223a2231303030227d
68

Control block:
c150be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3
```

**Script byte-by-byte decode:**

| Bytes | Hex | Meaning |
|-------|-----|---------|
| 1 | `20` | OP_PUSHBYTES_32 |
| 2–33 | `50be5fc4...bb4d3` | x-only public key |
| 34 | `ac` | OP_CHECKSIG |
| 35 | `00` | OP_0 (condition false) |
| 36 | `63` | OP_IF |
| 37 | `03` | OP_PUSHBYTES_3 |
| 38–40 | `6f7264` | `"ord"` |
| 41 | `51` | OP_PUSHNUM_1 |
| 42 | `18` | OP_PUSHBYTES_24 |
| 43–66 | `74657874...7574662d38` | `"text/plain;charset=utf-8"` |
| 67 | `00` | OP_0 |
| 68 | `35` | OP_PUSHBYTES_53 |
| 69–121 | `7b2270...227d` | `{"p":"brc-20","op":"mint","tick":"DEMO","amt":"1000"}` |
| 122 | `68` | OP_ENDIF |

**Control block** (33 bytes):

```
c1  50be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3
```

First byte `0xc1`: parity bit = 1, leaf version = `0xc0` (Tapscript). The remaining 32 bytes are the internal public key. A single-leaf tree requires no Merkle path; the control block is 33 bytes, identical in structure to the single-leaf control block in Chapter 7.

---

## Code: Building the Inscription Leaf and Temporary Address

```python
private_key = PrivateKey.from_wif("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
public_key = private_key.get_public_key()

MINT_JSON = {"p": "brc-20", "op": "mint", "tick": "DEMO", "amt": "1000"}
brc20_hex = json.dumps(MINT_JSON, separators=(',', ':')).encode('utf-8').hex()

inscription_script = Script([
    public_key.to_x_only_hex(),
    "OP_CHECKSIG",
    "OP_0",
    "OP_IF",
    "6f7264",                                             # "ord"
    "OP_1",
    "746578742f706c61696e3b636861727365743d7574662d38",  # "text/plain;charset=utf-8"
    "OP_0",
    brc20_hex,
    "OP_ENDIF"
])

temp_address = public_key.get_taproot_address([[inscription_script]])
print(temp_address.to_string())
# tb1pe7dahu72sdy64u449nw3k8u36gptxvccgyvmqn0t02t8pcceym5seqqfsp
```

`get_taproot_address([[inscription_script]])` takes a single-leaf list, the same call pattern as Chapter 7. The generated address can be verified against output 0 of the commit transaction.

---

## Code: Commit and Reveal (Key Fragments)

Complete runnable scripts are in `code/chapter09/`.

**Commit** — key path, witness contains one signature:

```python
sig = private_key.sign_taproot_input(
    commit_tx, 0,
    [key_path_address.to_script_pub_key()],
    [utxo_amount],
    script_path=False
)
commit_tx.witnesses.append(TxWitnessInput([sig]))
# commit txid: 515ddcfc...1f950aa0
```

**Reveal** — script path, witness is the three-element set:

```python
sig = private_key.sign_taproot_input(
    reveal_tx, 0,
    [temp_address.to_script_pub_key()],
    [inscription_amount],
    script_path=True,
    tapleaf_script=inscription_script,
    tweak=False
)
control_block = ControlBlock(
    public_key,
    [[inscription_script]],
    0,
    is_odd=temp_address.is_odd()
)
reveal_tx.witnesses.append(TxWitnessInput([
    sig,
    inscription_script.to_hex(),
    control_block.to_hex()
]))
# reveal txid: 2fc169a5...fff57547
```

The `sign_taproot_input` parameters match the script-path signing in Chapter 7. `ControlBlock` takes the single-leaf list and leaf index `0`.

---

## Indexer

This transaction is a valid Tapscript spend: signature valid, script format correct. The indexer scans the reveal witness, locates the `OP_0 OP_IF ... OP_ENDIF` segment, extracts the JSON, and computes state according to its protocol rules — all off-chain.

Different indexers can produce different interpretations of the same on-chain history. Divergences between ord versions have occurred in practice, causing different indexers to report different balances for the same mint operation on different exchanges. The correctness of these protocols ultimately depends on trust in a specific indexer.

---

## Chapter Summary

A large number of Ordinals and BRC-20 transactions share the same on-chain structure: a single-leaf Taproot script path, with an `OP_0 OP_IF ... OP_ENDIF` envelope in the leaf, commit to lock, reveal to publish. The VM validates the signature and script format, skips the data segment; the meaning of that data is determined by off-chain indexers.

The next chapter covers RGB: also a combination of Taproot outputs and an off-chain protocol, but using single-use seals to bring the protocol's security boundary back to a verifiable on-chain commitment — a fundamentally different trust model from the indexer dependency here.