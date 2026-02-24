# Submission — Mpumelelo Ntobi

Replace "Your Name" with your name or handle.

---

## 1. UTXO vs Physical Cash

*Where does the analogy break?*
- Physical cash does not get destroyed to create new physical cash
---

## 2. "Sending to an Address"

*Why is this technically misleading?*
- The concept of an address in Bitcoin does not refer to a physical or digital location where something can be sent to (move from current location to a destination location)
- Instead, it is more like locking to a locking script (spending conditions)
---

## 3. Whitepaper vs P2PKH

*What changed structurally?*
- From payment to a public key (original implementation) to payment to a public key hash

---

## 4. Balance as Query

*Why is wallet balance a computed result, not a stored value?*
- The are no balances being recorded and tracked in the bitcoin network 
- Wallet balance is calculated through some logic built into the wallet which goes into the blockchain, identify and sum all UTXO which belongs to the wallet (private key belonging to the wallet)

---

## Reflection

What concept still feels unclear?
- The impact of the publicly published unlocking script on privacy 
    - Can an attacker take a signature / unlocking script from the blockchain and maliciously reuse it?
- The future / quantum computing proof of addresses 
    - Won't a quantum computer be able to apply brute force to get the public and from the public key do a second brute force to get the private key?
