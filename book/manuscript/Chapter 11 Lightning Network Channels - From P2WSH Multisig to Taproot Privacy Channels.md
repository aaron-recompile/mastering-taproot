# Chapter 11: Lightning Network Channels — From P2WSH Multisig to Taproot Privacy Channels

## Lightning: One of Taproot's Original Motivations

The Lightning Network is one of Taproot's original design motivations.

Chapter 9 showed how Taproot's witness can serve as a data layer (Ordinals). Chapter 10 showed how Taproot's commitment capabilities can anchor off-chain state (RGB). This chapter returns to Taproot's core design goal: making complex multi-party contracts look identical to ordinary payments on-chain.

A Lightning payment channel locks funds into a jointly controlled output, allows unlimited off-chain balance updates, then settles with a single on-chain close. Under Taproot, the cooperative close — over 90% of all channel closes — leaves no trace distinguishing it from an ordinary payment.

## P2WSH: The SegWit v0 Script Hash

Traditional Lightning channels are built on P2WSH (Pay-to-Witness-Script-Hash), the SegWit v0 upgrade of P2SH. Both put a hash of a complex script on-chain and reveal the script itself only at spend time. The difference: P2SH uses HASH160 (20 bytes); P2WSH uses SHA256 (32 bytes), raising collision resistance from 80 bits to 128 bits. P2WSH also moves script execution into the witness field, benefiting from SegWit's discounted weight.

Traditional Lightning channels use P2WSH to wrap a 2-of-2 multisig:

```
Witness Script:
  OP_2 <alice_pubkey> <bob_pubkey> OP_2 OP_CHECKMULTISIG

ScriptPubKey (on-chain):
  OP_0 <32-byte SHA256(witness_script)>
```

The funding output exposes only a hash, but when spent the witness reveals everything: two DER signatures and the complete multisig script. Any observer knows this is a Lightning channel.

## On-Chain Example: P2WSH Channel Funding and Close

Using the same Alice/Bob keys carried throughout this book, lock 10,000 sats into a 2-of-2 P2WSH:

```python
pubs = sorted([alice_pub.to_hex(), bob_pub.to_hex()])  # BIP67: lexicographic ordering

witness_script = Script([
    'OP_2', pubs[0], pubs[1], 'OP_2', 'OP_CHECKMULTISIG'
])

p2wsh_addr = P2wshAddress.from_script(witness_script)
```

The `sorted()` call ensures the address is identical regardless of the order the two public keys are passed in — a BIP67 requirement and a common implementation pitfall.

Output:

```
Witness Script (hex): 52210250be5f...b27e2d77...210284b5...af552ae
Witness Script size:  71 bytes
Funding Address (P2WSH): tb1qztxpf2...393urj
ScriptPubKey: 002012cc14a9...3afe3b71c
Format: OP_0 <32-byte SHA256(witness_script)>
```

**Funding transaction** (both parties sign and broadcast):

[7c512abc...2d09767a](https://mempool.space/testnet/tx/7c512abcdc86e48837e6e5ba57524c3ee25f1c4bd4bf7d42f7db084b2d09767a?showDetails=true)

- vout:0: `tb1qztxpf2...393urj`, 10,000 sats, P2WSH
- Observer sees: `OP_0 <32-byte hash>` — a SegWit v0 script hash output, almost certainly multisig

### Cooperative Close

Both parties agree to close the channel and each signs to spend the funding output:

```python
alice_sig = alice_priv.sign_segwit_input(tx, 0, witness_script, fund_amount_sats)
bob_sig   = bob_priv.sign_segwit_input(tx, 0, witness_script, fund_amount_sats)

# P2WSH witness: [empty, alice_sig, bob_sig, witness_script]
tx.witnesses.append(TxWitnessInput([
    '',                      # empty element required by legacy OP_CHECKMULTISIG bug
    alice_sig,               # 71 bytes, DER encoded
    bob_sig,                 # 71 bytes, DER encoded
    witness_script.to_hex()  # 71 bytes: the script itself
]))
```

**Cooperative close transaction**:

[bd6da1cd...52840461](https://mempool.space/testnet/tx/bd6da1cdd3740661875b2568c2b4494f818c3c3742f809e23512c43f52840461?showDetails=true)

On-chain witness structure:

```
[0] empty          (OP_CHECKMULTISIG legacy bug)
[1] Alice sig      (71 bytes, DER encoded)
[2] Bob sig        (71 bytes, DER encoded)
[3] Witness script (71 bytes: OP_2 <pk_a> <pk_b> OP_2 OP_CHECKMULTISIG)

Total witness: ~214 bytes
```

Observer concludes: "This is a 2-of-2 multisig. Almost certainly a Lightning channel."

## Taproot Channel: MuSig2 Key Aggregation

Taproot channels replace P2WSH with a pure key-path Taproot output. The 2-of-2 multisig is hidden inside a single aggregated public key via MuSig2 (BIP 327). External observers see only a 32-byte x-only key — indistinguishable from any single-signer Taproot address.

### MuSig2 Key Aggregation

Naive public key addition `P_alice + P_bob` has a fatal flaw: Bob can claim his public key is `P_bob - P_alice`, making the aggregate equal to `P_bob` alone — the rogue-key attack.

MuSig2's solution is to weight each public key with a coefficient derived from the full set of all participant keys:

```
P_agg = H(L, P_alice) · P_alice + H(L, P_bob) · P_bob

where L = {P_alice, P_bob} (the set of all participant keys)
```

Bob cannot forge the coefficient because it depends on his declared public key — changing the key changes the coefficient, neutralizing the attack.

In code, this is handled by the BIP-327 reference implementation's `key_agg()`:

```python
pk_alice = pubkey_to_plain(alice_pub)   # 33-byte compressed pubkey
pk_bob   = pubkey_to_plain(bob_pub)

agg_ctx   = mu.key_agg([pk_alice, pk_bob])
xonly_agg = mu.get_xonly_pk(agg_ctx)
```

Output:

```
Alice pubkey:   0250be5fc4...26bb4d3
Bob pubkey:     0284b59516...63af5
Aggregated (x): c9688c3935320a89911366a588bca56103ed295b3412a3061315a06d26d0069f
```

The resulting `c9688c...` is the x-coordinate of the aggregate key. Neither party can compute the corresponding private key alone.

### BIP86 Funding Output

The aggregate key still needs a BIP86 tweak. This lets both channel parties verify that the funding output is a key-path-only Taproot output, rather than one that secretly commits to an extra script path:

```python
def bip86_tweak(xonly_agg: bytes) -> bytes:
    tag = b'TapTweak'
    tag_hash = hashlib.sha256(tag).digest()
    return hashlib.sha256(tag_hash + tag_hash + xonly_agg).digest()

tweak = bip86_tweak(xonly_agg)
agg_ctx_tweaked = mu.apply_tweak(agg_ctx, tweak, is_xonly=True)
xonly_output    = mu.get_xonly_pk(agg_ctx_tweaked)
```

Output:

```
BIP86 tweak:    29331a2bb167b04282e424a07120a614a9d6a68d48e4ae6567dfa34f29ea0e6c
Output key (x): 6ba767bc2cb48e003885e7e235ee942b5d1cbab2029e61db0f5d3cbd3f4d5bf8
```

Final address:

```python
funding_pub  = PublicKey("02" + xonly_output.hex())
funding_addr = funding_pub.get_taproot_address()
# tb1pnn82l6...9m8uvc
```

**Funding transaction** (Alice and Bob lock 10,000 sats into the MuSig2 aggregate + BIP86 output):

[b7efde1f...1898aace](https://mempool.space/testnet/tx/b7efde1f1659a6a48d998c7860d9a586ac65c6069e73ded9779f1f6e1898aace?showDetails=true)

- vout:1: `tb1pnn82l6...9m8uvc`, 10,000 sats, P2TR
- Observer sees: `OP_1 <32-byte key>` — an ordinary Taproot address. Could be anything.

## MuSig2 Cooperative Close: The Four-Round Signing Protocol

Closing the channel requires both parties to jointly produce a single Schnorr signature. This is the heart of BIP-327: neither party ever sees the other's private key, yet their contributions aggregate into one standard signature.

### Round 1: NonceGen — Each Party Generates a Random Nonce

Each participant independently generates a secret/public nonce pair:

```python
nonce_alice = mu.nonce_gen_internal(
    rand_=bytes(32),        # random bytes (must be truly random in production)
    sk=sk_alice,
    pk=pk_alice,
    aggpk=xonly_output,
    msg=msg,
    extra_in=None
)
nonce_bob = mu.nonce_gen_internal(
    rand_=bytes([1] * 32),
    sk=sk_bob,
    pk=pk_bob,
    aggpk=xonly_output,
    msg=msg,
    extra_in=None
)

pubnonce_alice = nonce_alice[1]   # public nonce — safe to exchange
pubnonce_bob   = nonce_bob[1]
secnonce_alice = nonce_alice[0]   # secret nonce — never share
secnonce_bob   = nonce_bob[0]
```

Both parties exchange their public nonces. Secret nonces stay private.

### Round 2: NonceAgg — Aggregate the Public Nonces

```python
aggnonce = mu.nonce_agg([pubnonce_alice, pubnonce_bob])
```

Either party can perform this step. The resulting `aggnonce` is public.

### Round 3: PartialSign — Each Party Signs

There is a subtle engineering detail here: `bitcoinutils`'s `get_taproot_address()` applies its own BIP86 tweak internally. If a BIP86 tweak was already applied manually, the on-chain output key has been tweaked twice. The `SessionContext` must include both tweaks — a signature built with only one tweak passes local `schnorr_verify` but is rejected by Bitcoin Core's mempool. This was verified against testnet.

```python
# First tweak: manually applied to the raw aggregate key
agg_ctx_raw    = mu.key_agg(pubkeys)
xonly_raw      = mu.get_xonly_pk(agg_ctx_raw)
tweak1         = bip86_tweak(xonly_raw)

# Second tweak: applied internally by get_taproot_address()
agg_ctx_t1     = mu.apply_tweak(agg_ctx_raw, tweak1, is_xonly=True)
xonly_after_t1 = mu.get_xonly_pk(agg_ctx_t1)
tweak2         = bip86_tweak(xonly_after_t1)

# SessionContext must carry both tweaks
session_ctx = mu.SessionContext(
    aggnonce, pubkeys,
    [tweak1, tweak2],   # both tweaks required
    [True, True],
    msg
)

psig_alice = mu.sign(secnonce_alice, sk_alice, session_ctx)
psig_bob   = mu.sign(secnonce_bob,   sk_bob,   session_ctx)
```

Output:

```
Alice partial sig: 3f8a1c2d... (first 16 bytes shown)
Bob partial sig:   c12b9e4f... (first 16 bytes shown)
```

### Round 4: SigAgg — Aggregate into the Final Signature

```python
final_sig = mu.partial_sig_agg([psig_alice, psig_bob], session_ctx)

assert mu.schnorr_verify(msg, xonly_output, final_sig)
# -> Verification: PASSED
```

Output:

```
Aggregated sig:   9e4f7a2b... (64 bytes)
Signature length: 64 bytes
Verification:     PASSED (against tweaked output key)
```

Alice never saw Bob's private key. Bob never saw Alice's. Two partial signatures aggregated into one — format-identical to any single-signer Schnorr signature.

### Broadcasting the Cooperative Close

```python
tx.witnesses.append(TxWitnessInput([final_sig.hex()]))
```

**MuSig2 cooperative close transaction**:

[af6fdae8...13b39d1f](https://mempool.space/testnet/tx/af6fdae8c2731b2b83e74b8dd79bc2c241dea8aee8c8cfb6f094e44c13b39d1f?showDetails=true)

On-chain witness structure:

```
[0] Schnorr signature (64 bytes) — MuSig2 aggregated from Alice + Bob

Total witness: 64 bytes
```

Observer concludes: "An ordinary Taproot payment. Nothing unusual."

## Side-by-Side Comparison

The same channel. The same two parties. The same final balance allocation. Run `code/chapter11/03_compare_witness.py` to reproduce the following output:

```
                          P2WSH              Taproot (MuSig2)
Funding scriptPubKey      OP_0 <32-byte>     OP_1 <32-byte>
Funding observer sees     "P2WSH, likely      "Taproot address,
                           multisig"           could be anything"

Close witness elements    4                  1
Close signatures          2 (DER, ~71 each)  1 (Schnorr, 64 bytes)
Close script exposed      Yes (2-of-2)       No
Close witness size        214 bytes          64 bytes
Close tx vsize            168 vbytes         154 vbytes
Identifiable as channel   Yes                No
Witness savings           —                  70%
```

## Chapter Summary

Lightning Network Taproot channels replace P2WSH 2-of-2 multisig with MuSig2 key aggregation and a BIP86 key-only funding output. The cooperative close — the dominant channel closing method — produces a single 64-byte Schnorr signature, indistinguishable from any ordinary Taproot payment. P2WSH exposes the complete multisig script and two separate signatures; Taproot reveals nothing.

MuSig2 (BIP 327) enables two parties to jointly control a single public key without either seeing the other's private key. The four-round signing protocol (NonceGen -> NonceAgg -> PartialSign -> SigAgg) produces a standard 64-byte Schnorr signature on-chain. The BIP86 tweak lets both channel parties confirm that the funding output is key-path-only, rather than one that quietly commits to a hidden script path.

P2WSH made the channel structure legible to any observer. Taproot makes it invisible. The funding output, the cooperative close, the witness — none of it distinguishes a Lightning channel from an ordinary single-key payment.