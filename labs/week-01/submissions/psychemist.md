# Submission — psychemist

---

## 1. UTXO vs Physical Cash

*Where does the analogy break?*

A UTXO (Unspent Transaction Output) is like physical cash because it cannot be divided, so, one has to spend it entirely then send a new UTXO representing change, if necessary. This analogy falls apart when you consider that a UTXO is typically cryptographically locked to a script and can only be spent by the owner (one or more people) who can produce the required signature/data to unlock it. However, physical cash can be exchanged and used by millions of people without any specific spending conditions.  

UTXOs also have unique identifiers (txid, vout) which recursively link their history from the previous spender who created that UTXO back to the genesis block, effectively making them pseudonymous. Physical cash has identifying metadata (year of mint, serial number) but those are not linked to spenders, making cash effectively anonymous.

---

## 2. "Sending to an Address"

*Why is this technically misleading?*

Sending to a Bitcoin address is misleading because the protocol does not store any addresses or perform transactions with addresses. Value is tied to the output's scriptPubkey, typically a hash of a public key, the public key itself, or the hash of a more complex script such as multisig.  

In the ledger, the UTXO set deletes the current UTXO being spent and creates a new UTXO that is unlockable by the receiver. Also, the transaction being spent is deleted from the mempool and mined in a new block, preventing double-spending. From a programmer’s perspective, we are creating new UTXO objects that store some state about a possibly spendable value, recording the amount and new owner (party that unlocks script).

---

## 3. Whitepaper vs P2PKH

*What changed structurally?*

The v1 version of the Bitcoin protocol proposed in the whitepaper sent value by signing the hash of the previous transaction and the receiver's public key. The receiver could then prove their owership by verifying the signature using their public key.  In P2PKH, the scriptPubkey contains the HASH160 of a public key and a more elaborate locking/unlocking mechanism using the Script programming language.  

These changes were necessary because:  

1. Hashing the public key before committing it to the blockchai adds a second layer of protection in a post-quantum world where the ECDSA encryption is broken.
2. Reducing the size of the scriptPubkey from 65 bytes (uncompressed public key) to 20 bytes (output of RIPEMD(SHA256(SHA256(public key)))).

---

## 4. Balance as Query

*Why is wallet balance a computed result, not a stored value?*

Balance is not a stored value because it is constantly computed from all the entries in the global trasaction set that are spendable by all the public keys in a user's wallet (UTXO pool).  

When you open your wallet and see a balance, that number is the result of a computation:  

1. the wallet uses the HD scheme to generate public keys (up to a level) from the private keys it currently holds
2. from these public keys, it computes scriptPubkeys based on the different script types (P2PKH, P2SH, P2WPKH, P2TR)
3. it scans all transactions in the global UTXO set and compares the value contained in each UTXO output's scriptPubkey field to those gotten from step 2
4. if any is a match, it adds that UTXO to the local UTXO set
5. it iterates over this UTXO set and sums the amount of each to get a total value, which is the wallet balance. this balance is not stored on-chain

---

## Reflection

What concept still feels unclear?  
Keypath vs ScriptPath spending flow from start to finish
