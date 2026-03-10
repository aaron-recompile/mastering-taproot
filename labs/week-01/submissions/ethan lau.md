Submission — **ethan lau**

### 1. UTXO vs Physical Cash

**Where does the analogy break?**

A UTXO (Unspent Transaction Output) is often compared to physical cash because both represent discrete units of value that can be spent. However, the analogy breaks because physical cash is a physical object that is directly transferred between people, while a UTXO is simply a record in a distributed ledger.

In Bitcoin, spending does not move coins from one place to another. Instead, a transaction consumes existing UTXOs and creates new ones. Ownership is defined by the ability to satisfy the locking script with the correct cryptographic signature, not by physical possession.

**Differences**

| Feature       | Physical Cash                       | UTXO                                       |
| ------------- | ----------------------------------- | ------------------------------------------ |
| Transfer      | Physical handover                   | Broadcast a transaction to the network     |
| Coin Identity | The same bill continues circulating | UTXO is destroyed and new ones are created |
| Location      | Stored physically                   | Recorded on the global ledger              |
| Ownership     | Possession of the bill              | Ability to unlock the script with a key    |
| Double Spend  | Impossible physically               | Prevented through network consensus        |

---

### 2. "Sending to an Address"

**Why is this technically misleading?**

The phrase “sending Bitcoin to an address” is technically misleading because Bitcoin does not move coins between locations, and addresses are not actually stored in the protocol. Instead, transactions create outputs that contain locking scripts defining the conditions required to spend them.

An address is simply a human-friendly representation of those spending conditions, typically derived from a public key hash. The value remains recorded on the global ledger, and anyone who can provide the correct unlocking data (such as a signature and public key) can spend that output.

---

### 3. Whitepaper vs P2PKH

**What changed structurally?**

The Bitcoin whitepaper originally described transactions that paid directly to a public key (Pay-to-Public-Key, or P2PK). In this design, the locking script contained the receiver’s public key, and the spender would provide a signature to prove ownership of the corresponding private key.

This later evolved into Pay-to-Public-Key-Hash (P2PKH), where the transaction output contains a hash of the public key instead of the key itself. When spending the output, the spender must reveal the public key and provide a valid signature.

This change improved privacy by hiding the public key until the coins are spent, reduced the size of transaction outputs, and introduced the address format commonly used in Bitcoin wallets.

---

### 4. Balance as Query

**Why is wallet balance a computed result, not a stored value?**

Bitcoin does not store balances as numbers on the blockchain. Instead, the blockchain records transactions that create and spend UTXOs. A wallet’s balance is therefore calculated by summing all UTXOs that can be unlocked by the wallet’s keys.

Because the blockchain follows an append-only model where past data cannot be modified, balances cannot simply be updated. Instead, they must be computed by scanning the UTXO set and identifying outputs that belong to the wallet.

---

### Reflection

**What concept still feels unclear?**

The purpose and design motivations behind newer upgrades such as SegWit and Taproot are clearer at a high level, but the detailed mechanics and tradeoffs behind their implementation still require deeper understanding.

