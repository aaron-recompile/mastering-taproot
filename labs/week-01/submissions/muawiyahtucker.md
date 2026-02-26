# Submission — Your Name

Replace "Your Name" with your name or handle.
Muaawiyah Tucker
CryptoHashReview
https://github.com/muaawiyahtucker
---

## 1. UTXO vs Physical Cash

*Where does the analogy break?*
A UTXO is just a pointer on a ledger that represents ownership of some amount of bitcoins. When it's spent, that pointer doesnt change nor is it 'given' to the recipient. Instead, the UTXO is destroyed as an "unspent" state and the recipient gets a new UTXO with that "unspent" attribute.
"Real" cash hands over the item which one could also claim is also just a 'placeholder' for ownership of some amount of 'value'. But the physical cash is not destroyed like a UTXO, it is transferred.

---

## 2. "Sending to an Address"

*Why is this technically misleading?*
The address just contains the terms by which the network accepts it to be later spent. Maybe a more accurate term would be to say:
"Sending to a contract by which the network prevents the spending of that value without cryptographic proof that the owner of the private key has authorized the funds to move to another contract, or other terms of the contract if those terms aren't defined by the private key."

---

## 3. Whitepaper vs P2PKH

*What changed structurally?*
The whitepaper tied the transfer of value from one digital signature to another, as stated in the statement " Each owner transfers the coin to the next by digitally signing a hash of the previous transaction and the public key of the next owner and adding these to the end of the coin". P2PKH changed this by tying it to the hash of the public key, and a script that verifies this. So there were now a series of OP_CODES that played a detailed role in how value was transferred.
---

## 4. Balance as Query

*Why is wallet balance a computed result, not a stored value?*
This because it is dependant upon assessing which UTXO's aren't spent yet and are therefore available for spending. The state of the blockchain changes constantly, so this 'tally' or total can change with each block added to the chain. That means a wallet needs to constantly be checking the current state of the blockchain in order to accurately assess what is the total amount of UTXO's that are available.
---

## Reflection

What concept still feels unclear?
