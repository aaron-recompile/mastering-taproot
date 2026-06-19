# Chapter 2: Bitcoin Script Fundamentals - Stack Operations and P2PKH

Chapter 1 ended on a single idea: an address is never more than a stand-in for a locking script. This chapter is about that script. Before any of it runs, though, you need to know what the script is actually locking — so we start with the UTXO model, then introduce Bitcoin Script and trace a real P2PKH spend through the stack, opcode by opcode. Everything Taproot does later is built on this same execution model.

## 2.1 The UTXO Model: Digital Cash, Not Digital Banking

Before looking at scripts, it helps to be precise about how Bitcoin holds value. It does not keep account balances. It uses the **Unspent Transaction Output (UTXO)** model, which behaves far more like physical cash than like a bank account.

### Cash vs. Banking: A Mental Model

A bank account is a single number that goes up and down. Cash is a handful of discrete bills, and you spend by handing over whole bills and taking change. Bitcoin works the second way.

**Traditional Banking (Account Model)**:

- Your account shows a balance: $500
- Spending $350 simply deducts from your balance
- Result: Account balance updates to $150
- No need to handle "change"

**Bitcoin UTXO Model (Cash Model)**:

- You don't have a "$500 balance"
- Instead, you have specific "bills": one $200 bill and three $100 bills
- To spend $350, you must provide $400 worth of bills ($200 + $100 + $100)
- You receive $50 in change as a new "bill"
- Result: You now have one $100 bill and one $50 bill

That cash-like behavior is not a quirk of the interface — it is the foundation of Bitcoin's design and security model.

### UTXO Model in Practice

Trace a single payment from Alice to Bob.

**Initial State**:

- Alice owns a 10 BTC UTXO
- Bob owns no bitcoin

**Alice sends 7 BTC to Bob**:

1. **Transaction Input**: Alice's 10 BTC UTXO (must be consumed entirely)
2. **Transaction Outputs**:
    - 7 BTC to Bob (new UTXO)
    - 3 BTC change back to Alice (new UTXO)
3. **Result**: The original 10 BTC UTXO is destroyed, two new UTXOs are created

Each UTXO is named by the transaction that created it plus its position in that transaction's output list — `transaction_id:output_index`:

- Bob's UTXO: `TX123:0` (7 BTC)
- Alice's change: `TX123:1` (3 BTC)

### Key UTXO Properties

A few properties follow directly from the cash model, and they are worth stating because the rest of the book leans on them:

- **Complete Consumption**: UTXOs must be spent in their entirety — no partial spending.
- **Atomic Creation**: Transactions either succeed completely (all inputs consumed, all outputs created) or fail completely.
- **Change Handling**: Any difference between input and output amounts becomes the transaction fee, unless explicitly returned as change.
- **Parallel Processing**: Since each UTXO can only be spent once, multiple transactions can be validated in parallel without complex state management.

## 2.2 Bitcoin Script and P2PKH Fundamentals

### Bitcoin Script: Programmable Spending Conditions

A UTXO carries more than an amount. It carries a **locking script** (ScriptPubKey) that states the conditions under which it can be spent. Spending it means supplying an **unlocking script** (ScriptSig) that satisfies those conditions. The two are checked together, and only then does the network treat the spend as valid.

### Script Architecture

```
Unlocking Script (ScriptSig) + Locking Script (ScriptPubKey) -> Valid/Invalid

```

**Locking Script (ScriptPubKey)**:

- Attached to each UTXO output
- Defines spending conditions
- Example: "Only spendable by someone who can provide a valid signature for public key X"

**Unlocking Script (ScriptSig)**:

- Provided when spending a UTXO
- Contains data needed to satisfy the locking script
- Example: "Here's my signature and public key"

To validate, the node combines the two scripts, runs them as a single program, and accepts the spend only if the final result is TRUE.

### Stack-Based Execution

Bitcoin Script runs on a stack, the same model used by languages like Forth or PostScript. Every operation works on a Last-In-First-Out (LIFO) stack: data gets pushed on, opcodes pop their arguments off and push results back. A short arithmetic example shows the whole mechanism.

Initial Stack: Empty
```
│ (empty)                               │
└───────────────────────────────────────┘

```


PUSH 3

```
│ 3                                     │
└───────────────────────────────────────┘

```


PUSH 5
```

│ 5                                     │
│ 3                                     │
└───────────────────────────────────────┘
```

ADD Operation
```

│ 8                                     │
└───────────────────────────────────────┘
```
The ADD step is the pattern in miniature: pop the top two numbers (5, then 3), add them, push the result (8). Nothing else is going on. That predictability is exactly why the model can carry complex spending conditions without becoming a security liability.

### P2PKH: The Foundation Script

Pay-to-Public-Key-Hash (P2PKH) is the most fundamental script type, and the right place to learn the stack model before Taproot complicates it.

**P2PKH Locking Script**

```
OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG

```

In words: this UTXO is spendable by anyone who can present a public key that hashes to `pubkey_hash`, together with a valid signature from the matching private key.

**P2PKH Unlocking Script**

```
<signature> <public_key>

```

The spender provides two things: a digital signature proving control of the private key, and the public key itself, which the script will hash and check against the committed hash.

### Real-World Example: Satoshi to Hal Finney

Bitcoin's first ever payment — Satoshi Nakamoto sending 10 BTC to Hal Finney — is the natural example.

**Transaction ID**: [`f4184fc5...831e9e16`](https://mempool.space/tx/f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16?showDetails=true)

**Transaction Structure**:

- **Input**: Satoshi's coinbase UTXO (50 BTC from mining)
- **Outputs**:
    - 10 BTC to Hal Finney
    - 40 BTC change back to Satoshi

One caveat: that 2009 transaction used P2PK (Pay-to-Public-Key), embedding the public key directly in the locking script, not P2PKH. P2PKH came shortly after and became the norm, because hashing the public key is both smaller on-chain and keeps the key hidden until spend. The walkthrough below keeps Hal as the spender but uses a P2PKH script, so the stack trace matches the form Bitcoin actually settled on.

### Step-by-Step P2PKH Execution - Hal Finney Example

Take Hal later spending a P2PKH-locked 10 BTC and walk the script end to end.

**Locking Script** (from the UTXO):

```
OP_DUP OP_HASH160 OP_PUSHBYTES_20 c5b28d6bba91a2693a9b1876bcd3929323890fb2 OP_EQUALVERIFY OP_CHECKSIG

```

**Unlocking Script** (provided by Hal):

```
OP_PUSHBYTES_71 30440220576497b7e6f9b553c0aba0d8929432550e092db9c130aae37b84b545e7f4a36c022066cb982ed80608372c139d7bb9af335423d5280350fe3e06bd510e695480914f01

OP_PUSHBYTES_33 02898711e6bf63f5cbe1b38c05e89d6c391c59e9f8f695da44bf3d20ca674c8519

```

The unlocking script runs first, pushing its two items; then the locking script's opcodes consume them. Each step below shows the stack right after the operation named.

1. **Push Signature to Stack**:
```
    
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
```
    
2. **Push Public Key to Stack**:
```
    
│ 02898711...8519 (public_key)          │
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
``` 
3. **OP_DUP**: Duplicate the top stack item (public key):
```
    
│ 02898711...8519 (public_key)          │
│ 02898711...8519 (public_key)          │
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
```    
4. **OP_HASH160**: Hash the top stack item:
```
    
│ c5b28d6b...890fb2 (hash160_result)    │
│ 02898711...8519 (public_key)          │
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
``` 
5. **Push Expected Hash**: From the locking script:
```
    
│ c5b28d6b...890fb2 (expected_hash)     │
│ c5b28d6b...890fb2 (computed_hash)     │
│ 02898711...8519 (public_key)          │
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
```

6. **OP_EQUALVERIFY**: Compare top two items, remove both if equal:
```
    
│ 02898711...8519 (public_key)          │
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
(Script fails if hashes don't match)
```    
7. **OP_CHECKSIG**: Verify signature against public key and transaction:
```

│ 1 (TRUE)                              │
└───────────────────────────────────────┘
``` 
8. **Final Check**: The script succeeds because the only item left on the stack is non-zero.

### P2PKH Security Properties

Four properties fall out of this design, and each one matters later:

The public-key hash sits in front of the key itself, so the public key stays hidden until the first spend — a layer of **pre-image resistance** that also buys some margin against a future break in ECDSA. **OP_CHECKSIG** ties the spend to the private key cryptographically: only the holder of that key can produce a passing signature. Because the signature commits to the transaction's details, it doubles as an **integrity** check — alter the transaction after signing and the signature no longer verifies. And since each signature is bound to one specific transaction, it cannot be lifted and **replayed** elsewhere.

## 2.3 Practical Implementation: Building a P2PKH transaction

### Crafting a real testnet Legacy-to-SegWit transaction

The cleanest way to see all of this hold together is to build one real transaction. Below, a Legacy P2PKH input pays a SegWit output on testnet; afterward we take the broadcast result apart and trace its script on the stack.

```python
from bitcoinutils.setup import setup
from bitcoinutils.utils import to_satoshis
from bitcoinutils.transactions import Transaction, TxInput, TxOutput
from bitcoinutils.keys import P2wpkhAddress, P2pkhAddress, PrivateKey
from bitcoinutils.script import Script

def main():
    # Setup testnet environment
    setup('testnet')

    # Sender information - Legacy P2PKH
    private_key = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
    public_key = private_key.get_public_key()
    from_address_str = "myYHJtG3cyoRseuTwvViGHgP2efAvZkYa4"
    from_address = P2pkhAddress(from_address_str)

    # Receiver - SegWit address
    to_address = P2wpkhAddress('tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4')

    print(f"Sender Legacy Address: {from_address_str}")
    print(f"Receiver SegWit Address: {to_address.to_string()}")

    # Create transaction input (referencing previous UTXO)
    txin = TxInput(
        '34b90a15d0a9ec9ff3d7bed2536533c73278a9559391cb8c9778b7e7141806f7',
        1  # vout index
    )

    # Calculate amounts
    total_input = 0.00029606  # Input amount in BTC
    amount_to_send = 0.00029400  # Amount to send
    fee = total_input - amount_to_send  # Transaction fee

    # Create transaction output
    txout = TxOutput(to_satoshis(amount_to_send), to_address.to_script_pub_key())

    # Create unsigned transaction
    tx = Transaction([txin], [txout])

    print(f"Unsigned transaction: {tx.serialize()}")

    # Get the P2PKH locking script for signing
    p2pkh_script = from_address.to_script_pub_key()

    # Sign the transaction input
    signature = private_key.sign_input(tx, 0, p2pkh_script)

    # Create the unlocking script: <signature> <public_key>
    txin.script_sig = Script([signature, public_key.to_hex()])

    # Get the signed transaction
    signed_tx = tx.serialize()

    print(f"Signed transaction: {signed_tx}")
    print(f"Transaction size: {tx.get_size()} bytes")

if __name__ == "__main__":
    main()

```

### Key Functions and Components Explained

The script leans on three groups of `bitcoinutils` calls. Setup and keys come first: `setup('testnet')` points the library at testnet, `PrivateKey()` loads a key from WIF, and `P2pkhAddress()` / `P2wpkhAddress()` build address objects for the Legacy sender and the SegWit receiver. Construction follows: `TxInput()` references the UTXO being spent by txid and output index, `TxOutput()` sets destination and amount, `Transaction()` assembles them, and `to_satoshis()` converts BTC to satoshis (1 BTC = 100,000,000 satoshis). Finally the script and signature: `to_script_pub_key()` derives an address's locking script, `sign_input()` signs one input, and `Script()` packs the signature and public key into the unlocking script.

### Real Data Analysis and Stack Execution

Running the code produces a real transaction that was broadcast to testnet. We can pull its bytes back apart and confirm the script does exactly what the trace predicted.

**Transaction ID**: [`bf41b474...a8e58355`](https://mempool.space/testnet/tx/bf41b47481a9d1c99af0b62bb36bc864182312f39a3e1e06c8f6304ba8e58355?showDetails=true)

**Raw Transaction Data**:

```text
0200000001f7061814e7b778978ccb919355a97832c7336553d2bed7f39feca9
d0150ab934010000006a473044022055c309fe3f6099f4f881d0fd960923eb91af
f0d8ef3501a2fc04dce99aca609d0220174b9aec4fc22f6f81b637bbafec9554e4
97ec2d9f3ca4992ee4209dd047443d012102898711e6bf63f5cbe1b38c05e89d6c
391c59e9f8f695da44bf3d20ca674c8519ffffffff01d872000000000000160014
c5b28d6bba91a2693a9b1876bcd3929323890fb200000000
```

The unlocking script (ScriptSig) is the part that carries the spending proof. Pulled out of the raw bytes:

```text
473044022055c309fe3f6099f4f881d0fd960923eb91aff0d8ef3501a2fc04dce
99aca609d0220174b9aec4fc22f6f81b637bbafec9554e497ec2d9f3ca4992ee4
209dd047443d012102898711e6bf63f5cbe1b38c05e89d6c391c59e9f8f695da44
bf3d20ca674c8519
```

**Parsed Components**:

- `47`: OP_PUSHBYTES_71 (push 71 bytes - the signature)
- `304402...443d01`: DER-encoded signature (71 bytes)
- `21`: OP_PUSHBYTES_33 (push 33 bytes - the public key)
- `02898711...8519`: Compressed public key (33 bytes)

The locking script (ScriptPubKey) on the UTXO being spent is the standard P2PKH shape:

`76a914c5b28d6bba91a2693a9b1876bcd3929323890fb288ac`

**Parsed Locking Script**:

- `76`: OP_DUP
- `a9`: OP_HASH160
- `14`: OP_PUSHBYTES_20 (push 20 bytes)
- `c5b28d6bba91a2693a9b1876bcd3929323890fb2`: Public key hash (20 bytes)
- `88`: OP_EQUALVERIFY
- `ac`: OP_CHECKSIG

### Stack Execution Trace

With both scripts parsed, the execution runs step by step against the real data.

**Initial State**:

```
│ (empty)                               │
└───────────────────────────────────────┘
```
Script: <signature> <pubkey> OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG

**Step 1 - Push Signature**:

Operation: PUSH 304402...443d01
```
│ 304402...443d01 (signature)           │
└───────────────────────────────────────┘
```
**Step 2 - Push Public Key**:

Operation: PUSH 02898711...8519
```
│ 02898711...8519 (public_key)          │
│ 304402...443d01 (signature)           │
└───────────────────────────────────────┘
```
**Step 3 - OP_DUP**:

Operation: Duplicate top stack item
```
│ 02898711...8519 (public_key)          │
│ 02898711...8519 (public_key)          │
│ 304402...443d01 (signature)           │
└───────────────────────────────────────┘
```
**Step 4 - OP_HASH160**:

Operation: Hash160(top stack item)
Calculation: hash160(02898711...8519) = c5b28d6bba91a2693a9b1876bcd3929323890fb2
```
│ c5b28d6b...890fb2 (computed_hash)     │
│ 02898711...8519 (public_key)          │
│ 304402...443d01 (signature)           │
└───────────────────────────────────────┘
```
**Step 5 - Push Expected Hash**:

Operation: PUSH c5b28d6bba91a2693a9b1876bcd3929323890fb2
```
│ c5b28d6b...890fb2 (expected_hash)     │
│ c5b28d6b...890fb2 (computed_hash)     │
│ 02898711...8519 (public_key)          │
│ 304402...443d01 (signature)           │
└───────────────────────────────────────┘
```

**Step 6 - OP_EQUALVERIFY**:

Operation: Compare top two items, remove both if equal
Verification: c5b28d6b... == c5b28d6b... [OK] (Match)
```
│ 02898711...8519 (public_key)          │
│ 304402...443d01 (signature)           │
└───────────────────────────────────────┘
```
**Step 7 - OP_CHECKSIG**:

Operation: Verify signature against public key and transaction
Inputs:

Public key: 02898711...8519
Signature: 304402...443d01
Transaction data: (serialized transaction for signature)

Verification: ECDSA verification [OK] (Valid signature)
```
│ 1 (TRUE)                              │
└───────────────────────────────────────┘
```
**Final State**:
```
│ 1 (TRUE)                              │
└───────────────────────────────────────┘
```
Result: SUCCESS (non-zero value on stack)

### Transaction Broadcast Result

This transaction was accepted by the Bitcoin testnet and can be viewed here:
[`mempool.space/testnet/tx/bf41b474...a8e58355`](https://mempool.space/testnet/tx/bf41b47481a9d1c99af0b62bb36bc864182312f39a3e1e06c8f6304ba8e58355?showDetails=true)

A few things are worth reading off the result:

- The input references UTXO from transaction [`34b90a15...141806f7`](https://mempool.space/testnet/tx/34b90a15d0a9ec9ff3d7bed2536533c73278a9559391cb8c9778b7e7141806f7?showDetails=true) at index 1.
- The output sends 29,400 satoshis to a SegWit address.
- The fee is 206 satoshis (29,606 - 29,400) — the input minus the output, exactly as the UTXO model says.
- The signature proves ownership of the private key without ever putting the key on chain.

### What Carries Into the Next Chapters

P2PKH is the smallest complete example of Bitcoin's programmable money: stack-based execution, a hash commitment, and a signature check. Everything that follows reuses those three pieces and changes only what sits between them. P2SH (Chapter 3) hashes an entire *script* instead of a public key, so spending conditions can be arbitrarily complex while the address stays short. P2WPKH (Chapter 4) keeps P2PKH's logic but moves the signature into a separate witness, which fixes malleability. And P2TR (Chapter 5 onward) carries the same stack model into Schnorr signatures and Merkle-committed script trees. The opcodes get richer, but the execution model on this page does not change.

## Chapter Summary

This chapter set up the two things every later chapter assumes. The UTXO model holds value as discrete outputs, each consumed whole, which is what lets transactions validate in parallel with no shared balance to lock. And Bitcoin Script attaches a locking script to each output that an unlocking script must satisfy, checked together on a single LIFO stack.

- **P2PKH on the stack** — `OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG`: duplicate and hash the public key, confirm it matches the committed hash, then verify the signature.
- **From construction to chain** — using [`bitcoinutils`](https://github.com/karask/python-bitcoin-utils), we built, signed, and broadcast a real testnet P2PKH spend and traced its bytes back through the same seven steps.

**Next.** Chapter 3 moves to P2SH, which hides an entire script behind a single hash and reveals it only at spending time — the first step toward the script trees Taproot is built on.
