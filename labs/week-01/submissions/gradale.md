# Submission — gradale


## 1. UTXO vs Physical Cash

*Where does the analogy break?*

The UTXO model is a kind of state machine where transactions moves from old states and create new states, while physical notes imply ownership. 

Differences

| Feature |	Physical Cash|	UTXO |
| :--- | :--- | :--- |
| Transfer |	Physical handover |	Broadcasting a message to a global network |
| Coin Identity	| The bill or serial number persists over payment | The UTXO is destroyed and new ones are created |
|Location |	In your private pocket | Recorded on a global ledger, locked to your key| 
|Balance|	Sum of items | Set of references to the global ledger |
|Rules |	None (just value) |	Programmable (scripts, timelocks)|
|Double Spend|	Impossible |	Possible, but prevented by consensus |

---

## 2. "Sending to an Address"

*Why is this technically misleading?*

UTXO sent to you remains recorded on the global ledger, but locked to a specific cryptographic. Nobody owns it, you need the key to unlock it.

---

## 3. Whitepaper vs P2PKH

*What changed structurally?*

The primary locking mechanism was P2PK (Pay-to-Public-Key) , where the funds are locked directly to a public key, but it was replaced by P2PKH (Pay To Public Key Hash).

Diffrences 
- The public key is only revealed when the funds are spent, not when they are received
- Better usability as address is shorter and includes a checksum to protect against typos
- Locking Script - OP_EQUALVERIFY OP_CHECKSIG works as a two-part verification process: first prove you know the public key, then prove you own the private key.
- Unlocking Script - spender must now provide both the signature and the public key, matching the hash in the locking script.

---

## 4. Balance as Query

*Why is wallet balance a computed result, not a stored value?*

If balances were stored as a single number (ie state), updating that number would require modifying the blockchain data. But bitcoin blockchain is is a database of transactions with append-only model:

- Data can only be added, never modified or deleted
- Once a transaction is 6 blocks deep, it is impossible to change it, ie it's historically immutable by design

---

## Reflection

Segwit and Taproot purposes. It's clear how it's done, but not quite clear why
