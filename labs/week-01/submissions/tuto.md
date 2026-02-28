# Submission — tuto

---

## 1. UTXO vs Physical Cash

*Where does the analogy break?*

1. A spend does not move value from one container to another; it destroys old UTXOs and creates new UTXOs. In this process, entirely new outputs and new locking conditions are generated.
2. A UTXO is not a physically held object, but an on-chain state locked by `scriptPubKey`. Its "ownership" essentially means "I can satisfy the unlocking condition."
3. Authorization is based on cryptography and script validation (P2PKH, P2WPKH, P2TR), not physical possession.

---

## 2. "Sending to an Address"

*Why is this technically misleading?*

"Sending to an address" is only a simplified expression used by wallet software. When a transfer is executed on-chain, what the transaction actually creates is an output with a locking script, while the address is only a human-readable encoding of a script template.

- P2PKH: Encodes locking conditions related to `hash160`.
- SegWit: Encodes a witness program.
- Taproot: Encodes an x-only output public key (and may implicitly commit to a script tree via tweak).

So we are not "depositing coins into an address account"; we are creating a new UTXO whose spending conditions correspond to the script rules decoded from that address format.

---

## 3. Whitepaper vs P2PKH

*What changed structurally?*

The early whitepaper description was closer to a "public-key signature chain" model. Modern Bitcoin practice shifted to script locking (especially P2PKH), and later evolved to witness programs.

Main structural changes:

1. Shifted from "directly locking to a public key" to "locking to a public key hash" (P2PKH), which is more practical for privacy and key management.
2. Separated locking scripts (`scriptPubKey`) from unlocking data (`scriptSig` / witness), making verification flows composable and extensible.
3. Built a unified interface layer on top of raw scripts through standard script templates and address encoding.
4. SegWit separated witness data from the txid-critical serialization, fixing transaction malleability and paving the way for layer-2 protocols.
5. Taproot further unified the structure: the same output key supports both key path and script path, with selective disclosure.

---

## 4. Balance as Query

*Why is wallet balance a computed result, not a stored value?*

Bitcoin does not have a "global account balance field stored by wallet." A wallet balance is computed by querying the current UTXO set and selecting outputs that the wallet can unlock.

- Balance = the sum of unspent, spendable outputs I control.
- Confirmation status, locktime/sequence constraints, and script type all affect spendability.
- Every new block or mempool change can alter the spendable set, so balance is a dynamic query result.

---

## Reflection

What concept still feels unclear?

Taproot's practical use in real-world scenarios, its future expansion potential, and whether it is suitable for future AI agent interaction scenarios.
