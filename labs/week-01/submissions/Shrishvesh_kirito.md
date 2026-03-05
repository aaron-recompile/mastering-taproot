# Submission — Shrishvesh AKA kirito, 
Discord ID - yomanthunder
Display name - kirito
---

## 1. UTXO vs Physical Cash

*Where does the analogy break?*

When we refer to physical cash
- Has materialistic value, user can hold onto them but has a chance of losing them
- The payments made through this mode can be reversible (e.g: make a merchant payment, and steal the money from merchant without his/her consent, third party intermediaries like banks can intervine)
- Can be spent by anyone who holds the material, no proper athority over the asset 

When we refer UTXO - Unspent Transaction output

You have a transaction chain , where a user carries UTXO
UTXO can only be spent when the spending condition are met
when spending a UTXO it fully gets spent and an new UTXO is created, 
with the previous UXTO linked UTXO are put as inputs 
- Once the UTXO is spent, its is not reversible 
- This is a digital cash the user holds onto
- UTXO are locked with a spending condition, which often requires a signature
---

## 2. "Sending to an Address"

*Why is this technically misleading?*

Address is just a hash representation of public key with encoding, with use case of 
- Error detection
- Usability
- Shorter Identifier
- Simplyify the payment sharing info

Address does not store anyway value or amount, 
more clearly stated, spending to a address is misleading, 
Address can increase security in some cases where public key was never publically shared 

---

## 3. Whitepaper vs P2PKH

*What changed structurally?*

### P2PK : Pay To Public Key

scriptPubKey: `<pubkey> OP_CHECKSIG` <br>
scriptSig: `<signature>`

### P2PKH : Pay To Public Key Hash 

scriptPubKey: `OP_DUP OP_HASH160 <pubkeyHash> OP_EQUALVERIFY OP_CHECKSIG OP_CHECKSIG` <br>
scriptSig: `<signature> <pubkey>`

In the structure we stopped using a complete public key instead we use public key hash which is 
HASH160(pubkey)
Advantages 
- attacker must break hash first -> then attack ECC
- reduces output size, and enables the address system used in Bitcoin today
- pubkey - 65 bytes , pubkeyhash - 20 bytes
---

## 4. Balance as Query

*Why is wallet balance a computed result, not a stored value?*

UTXO can be spent only when spending conditions are met.
<br>
You hold a bunch of UTXOs
balance = sum(all UTXOs you can spend)
Wallets do not go over the entire blockchain to get amount you hold 

Instead wallet maintain a 
- maintain a UTXO set
- Or track UTXOs relevant to the wallet
Nodes already maintain a global UTXO database.

There by this makes easier to track the amount associated with address
---

## Reflection

What concept still feels unclear?

Taproot witness not having a pubkey hash ?
Script path spending usecase in taproot ? what is the advantage do we get from this ?
How the verification is taking place in case of Taproot Transaction ?
How is the stack present?
