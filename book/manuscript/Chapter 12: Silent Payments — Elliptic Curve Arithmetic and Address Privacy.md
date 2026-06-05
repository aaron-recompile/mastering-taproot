# Chapter 12: Silent Payments — Elliptic Curve Arithmetic and Address Privacy

## Why This Chapter Matters

Silent Payments (BIP352) solves a problem that requires no consensus change: the receiver publishes a static address once; each payment produces a fresh, unlinkable Taproot output. The chain sees an ordinary P2TR transfer.

The mathematical core is the same formula from Chapter 5's key tweaking: `P = Q + t·G`. The tweak `t` comes from an ECDH shared secret instead of a script tree Merkle root. If you understood Taproot's tweak, the math of Silent Payments is already in your hands.

---

## The Address Reuse Problem

Once a Bitcoin address is public, every payment to it is permanently visible on-chain and linked together. A donation page that publishes a receiving address exposes its complete payment history to anyone who looks. Using a fresh address for each payment requires coordinating with the sender in advance — impossible in a public-facing context.

Silent Payments work like this: the receiver (Bob) publishes a static address containing two public keys (`B_scan` and `B_spend`). The sender (Alice) takes her input private key `a`, performs ECDH with `B_scan` to get a shared secret, hashes it to derive the scalar `t`, then computes the one-time public key `P = B_spend + t·G` and pays to that address. The receiver uses the private key `b_scan` to perform the same ECDH against each transaction's input public key, re-derives `P`, and confirms a match. No interaction between the two parties. The chain sees an ordinary P2TR output.

ECDH guarantees this works: `a · (b_scan · G) = b_scan · (a · G)`, where `a` is Alice's input private key. Alice multiplies her private key by Bob's public key; Bob multiplies his private key by Alice's public key. The results are identical — neither party needs to share a private key to arrive at the same shared secret, and therefore the same `t`.

`b_scan`'s only role is to derive the tweak factor `t`. Spending uses `b_spend + t` — elliptic curve linearity guarantees that scalar addition mirrors point addition: `(b_spend + t)·G = B_spend + t·G = P`.

`t` is something both parties can derive independently, but only Bob holds `b_spend` — so only Bob can construct the spending key `b_spend + t`. Alice pays out; only Bob can claim.

Silent Payments turn "interaction" into key publication. Bob publishes `B_scan` in advance; Alice's payment transaction naturally exposes her input public key. Two public keys meet on-chain — a complete "interaction" with no communication required.

---

## On-Chain Example: Testnet Silent Payment

The following experiment was run on Bitcoin testnet using the book's Alice and Bob keys.

**Step 1: Derivation** (run `code/chapter12/01_silent_payment_derive.py`)

Bob's Silent Payment keys:

```
B_scan:  0368a9712c41bafbfa25d3e86d317d97b389083100818da112088fedbb7c929e10
B_spend: 02a5b069dcbb0458bac6aa04a2000c63ad93bc4853b35512913cee0b8f7214bcce
```

Alice's ECDH with Bob:

```
Alice input pubkey (A, visible on-chain, read by Bob when scanning):
  0250be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3

Alice computes with private key a:     a · B_scan  -> ECDH shared secret
Bob   computes with private key b_scan: b_scan · A  -> same shared secret

ECDH shared secret: 039e285df17d85590910f9e115422f29cfd32be28271845cd1abba62e542a1abc9
Tweak t:            026a61d9053ee35bd74560c408fa3aeeee397291bad7cef0b2ce50f24ef55630
One-time pubkey P:  03963061c3a266ae856b7755f2203e6d57e2ac9b9abf43f9414c05474eebea6e8b
```

One-time Taproot address: `tb1p9kq07ze6yu9lumrhgwrs9030nahrm7qq6cqjmz73a8ys9ya5rdvswnew3j`

Bob independently derives the same address using `b_scan · A` — match confirmed.

**Step 2: Send** (run `code/chapter12/02_send_testnet.py`)

Alice sends 5000 sats to the one-time address:

**Send transaction**: [b93523c5...f778e8](https://mempool.space/testnet/tx/b93523c5784080f1ca402bca39edda109e6e64c0df576c964e64630fb0f778e8)

On mempool.space:

- 1 input (Alice's Taproot UTXO), 2 outputs
- vout:0: `tb1p9kq07ze6yu9lumrhgwrs9030n...vswnew3j`, 5000 sats, V1_P2TR
- vout:1: Alice's change, V1_P2TR

No Silent Payment marker. No OP_RETURN. Indistinguishable from any Taproot transfer.

**Step 3: Bob scans and spends** (run `code/chapter12/03_bob_scan_and_spend.py`)

Bob extracts Alice's input pubkey from the transaction, computes `b_scan · A`, re-derives P, matches vout:0. Then computes the spending private key:

```
p = b_spend + t
p · G = (b_spend + t) · G = B_spend + t · G = P  [OK]
```

**Spend transaction**: [11774714...b8d91b](https://mempool.space/testnet/tx/11774714227d2c8c787372efff666dd0a27b044766e503a6241d28d2e1b8d91b)

Bob sends 4846 sats to his regular address. On-chain: another ordinary Taproot transfer. No link to Bob's Silent Payment address.

---

## The Mathematics: Same as Taproot's Tweak

Silent Payment address derivation and Taproot output key derivation share the same structure:

```
Taproot (Chapter 5):
  output_key = internal_key + t · G
  t = HashTapTweak(internal_key || merkle_root)

Silent Payment (this chapter):
  P = B_spend + t · G
  t = Hash("BIP0352/SharedSecret", shared_secret)
```

Both exploit elliptic curve linearity: point addition on public keys corresponds to scalar addition on private keys. The owner can always spend by adding the tweak to their private key.

Alice computes `a · B_scan`; Bob computes `b_scan · A`. The results are equal — the fundamental property of ECDH: `a · (b_scan · G) = b_scan · (a · G)`. No communication required. Both parties independently arrive at the same shared secret, then use it to derive the same output address.

---

## The Two-Key Split

Bob's static address contains two public keys, `B_scan` and `B_spend`, visible to anyone. The corresponding private keys have separate roles: `b_scan` can only perform ECDH to find which outputs belong to Bob — without `b_spend` it cannot spend anything, so it can safely be delegated to a scanning server. `b_spend` is the sole source of the spending key `b_spend + t` and must be kept strictly secret.

---

## Chapter Summary

Traditional receiving faces a dilemma: a fixed address is easy to publish but exposes payment history; a fresh address protects privacy but requires prior coordination. Silent Payments sidestep this — Bob publishes a static address, Alice's payment transaction naturally carries her public key, and the two complete an "interaction" on-chain with no communication, deriving a fresh one-time address every time.

When Bob scans for incoming payments, he performs ECDH against each transaction's input public key. If the derivation succeeds, the payment is confirmed as his and he can spend it.

This is privacy guaranteed by mathematics: no intermediary, no cooperation from the receiver required — the sender alone protects the privacy of both parties.

## Taproot Applications

With this chapter, the four frontier sections are complete — Taproot's representative applications in production. Every Taproot application grows the anonymity set for every other: Silent Payment outputs, Lightning channel closes, Ordinals minting, RGB state transitions — the on-chain format is identical across all of them, every one standard P2TR. Four chapters, four protocols, one on-chain footprint:

| Chapter | Application | Taproot Capability |
|---------|------------|-------------------|
| 9 | Ordinals | witness — store data |
| 10 | RGB | script path — hide commitment |
| 11 | Lightning | key path (cooperative close) + script path (contract structure) |
| 12 | Silent Payments | key path (public key naturally exposed) |

Taproot is still evolving. New protocols will be built on the same foundation. The goal of this book is to give you the tools to read them when they arrive.