# Submission — makuuchi_

Replace "Your Name" with your name or handle.

---

## 1. UTXO vs Physical Cash

*Where does the analogy break?*
- when making a cash transaction, there is no need to pay anyone a fee
- cash has a fixed set of input/output amounts, while a UTXO amount can be any multiple of a satoshi
- physical cash transactions don't need to be announced to all other physical cash holders
- physical cash doesn't offer me an easy way to verify that it's not counterfeit

---

## 2. "Sending to an Address"

*Why is this technically misleading?*
Because the bitcoin doesn't move from location a to location b. Instead, it remains in the same location, i.e. every full node's ledger. The bitcoin is merely re-grouped into different amounts, and locked with different spending conditions.

---

## 3. Whitepaper vs P2PKH

*What changed structurally?*
The white paper describes transactions that pay to a public key (P2PK), while P2PKH introduced transactions that pay to a public key hash. This boils down to different output locking scripts, and input unlocking scripts.

---

## 4. Balance as Query

*Why is wallet balance a computed result, not a stored value?*
The distributed nature of Bitcoin requires efficiency, since every full node needs to store the blockchain. That's why implied values are not stored, but computed. Wallet balance is one example of this, transaction fees another. Additionally, storing balances would reveal sensitive information.

---

## Reflection

What concept still feels unclear?

The math behind key aggregation.