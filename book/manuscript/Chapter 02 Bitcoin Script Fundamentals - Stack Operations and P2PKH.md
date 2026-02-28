# Chapter 2: Bitcoin Script Fundamentals - Stack Operations and P2PKH

Bitcoin's true innovation lies not just in digital signatures or decentralized consensus, but in its programmable money system. Every Bitcoin transaction is essentially a computer program that defines spending conditions. This chapter explores the foundational concepts that make Taproot possible: the UTXO model and Bitcoin Script.

## 2.1 The UTXO Model: Digital Cash, Not Digital Banking

Before diving into scripts, we must understand how Bitcoin represents value. Unlike traditional banking systems that maintain account balances, Bitcoin uses the **Unspent Transaction Output (UTXO)** model—a system that mimics physical cash more than digital bank accounts.

### Cash vs. Banking: A Mental Model

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

This cash-like behavior is fundamental to Bitcoin's design and security model.

### UTXO Model in Practice

Let's trace a simple transaction between Alice and Bob:

**Initial State**:

- Alice owns a 10 BTC UTXO
- Bob owns no bitcoin

**Alice sends 7 BTC to Bob**:

1. **Transaction Input**: Alice's 10 BTC UTXO (must be consumed entirely)
2. **Transaction Outputs**:
    - 7 BTC to Bob (new UTXO)
    - 3 BTC change back to Alice (new UTXO)
3. **Result**: The original 10 BTC UTXO is destroyed, two new UTXOs are created

**UTXO Identification**: Each UTXO is uniquely identified by `transaction_id:output_index`

- Bob's UTXO: `TX123:0` (7 BTC)
- Alice's change: `TX123:1` (3 BTC)

### Key UTXO Properties

- **Complete Consumption**: UTXOs must be spent in their entirety - no partial spending.
- **Atomic Creation**: Transactions either succeed completely (all inputs consumed, all outputs created) or fail completely.
- **Change Handling**: Any difference between input and output amounts becomes the transaction fee, unless explicitly returned as change.
- **Parallel Processing**: Since each UTXO can only be spent once, multiple transactions can be validated in parallel without complex state management.

## 2.2 Bitcoin Script and P2PKH Fundamentals

### Bitcoin Script: Programmable Spending Conditions

Each UTXO doesn't just contain an amount—it contains a **locking script** (ScriptPubKey) that defines the conditions under which it can be spent. To spend a UTXO, one must provide an **unlocking script** (ScriptSig) that satisfies these conditions.

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

**Validation Process**:

- Combine unlocking and locking scripts
- Execute as a single program
- If the final result is TRUE, the UTXO can be spent

### Stack-Based Execution

Bitcoin Script uses a stack-based execution model, similar to programming languages like Forth or PostScript. Operations manipulate a Last-In-First-Out (LIFO) stack:

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
Operation Process:

Pop two numbers from stack: 5 (top) and 3
Execute addition: 5 + 3 = 8
Push result 8 back to stack top

This simple model enables complex spending conditions while remaining predictable and secure.

### P2PKH: The Foundation Script

Pay-to-Public-Key-Hash (P2PKH) is Bitcoin's most fundamental script type and the foundation for understanding more complex scripts like those used in Taproot.

**P2PKH Locking Script**

```
OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG

```

This script means: "This UTXO can be spent by anyone who can provide a public key that hashes to `pubkey_hash` and a valid signature from the corresponding private key."

**P2PKH Unlocking Script**

```
<signature> <public_key>

```

The spender provides:

- A digital signature proving ownership of the private key
- The public key itself (which will be hashed and verified)

### Real-World Example: Satoshi to Hal Finney

Let's examine the famous first Bitcoin transaction: Satoshi Nakamoto sending 10 BTC to Hal Finney.

**Transaction ID**: [`f4184fc5...831e9e16`](https://mempool.space/tx/f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16?showDetails=true)

**Transaction Structure**:

- **Input**: Satoshi's coinbase UTXO (50 BTC from mining)
- **Outputs**:
    - 10 BTC to Hal Finney
    - 40 BTC change back to Satoshi

**Note**: This early transaction used P2PK (Pay-to-Public-Key) rather than P2PKH, directly embedding the public key in the locking script. Modern Bitcoin uses P2PKH for better security and space efficiency.

### Step-by-Step P2PKH Execution - Hal Finney Example

Let's trace through a P2PKH script execution using a real transaction. Consider Hal Finney later spending his 10 BTC:

**Locking Script** (from the UTXO):

```
OP_DUP OP_HASH160 OP_PUSHBYTES_20 340cfcffe029e6935f4e4e5839a2ff5f29c7a571 OP_EQUALVERIFY OP_CHECKSIG

```

**Unlocking Script** (provided by Hal):

```
OP_PUSHBYTES_71 30440220576497b7e6f9b553c0aba0d8929432550e092db9c130aae37b84b545e7f4a36c022066cb982ed80608372c139d7bb9af335423d5280350fe3e06bd510e695480914f01

OP_PUSHBYTES_33 02898711e6bf63f5cbe1b38c05e89d6c391c59e9f8f695da44bf3d20ca674c8519

```

**Execution Steps**:

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
    
│ 340cfcff...7a571 (hash160_result)     │
│ 02898711...8519 (public_key)          │
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
``` 
5. **Push Expected Hash**: From the locking script:
```
    
│ 340cfcff...7a571 (expected_hash)      │
│ 340cfcff...7a571 (computed_hash)      │
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
8. **Final Check**: Script succeeds if stack top is non-zero.

### P2PKH Security Properties

**Hash Pre-image Resistance**: The public key remains hidden until first spend, providing protection against potential quantum attacks on ECDSA.

**Signature Verification**: Cryptographically proves the spender controls the private key corresponding to the public key hash.

**Transaction Integrity**: The signature covers the transaction details, preventing modification after signing.

**Replay Protection**: Signatures are specific to particular transactions and cannot be reused.

## 2.3 Practical Implementation: Building a P2PKH transaction

### Crafting a real testnet Legacy-to-SegWit transaction

Let's build a complete P2PKH transaction step by step, explaining each component and then trace through the script execution with real data.

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

**Setup and Key Management**:

- `setup('testnet')`: Configures the library for testnet operations
- `PrivateKey()`: Creates a private key object from WIF format
- `P2pkhAddress()`: Creates a Legacy address object from address string
- `P2wpkhAddress()`: Creates a SegWit address object

**Transaction Construction**:

- `TxInput()`: References a previous UTXO by transaction ID and output index
- `TxOutput()`: Defines where coins are being sent and how much
- `Transaction()`: Combines inputs and outputs into a complete transaction
- `to_satoshis()`: Converts BTC amounts to satoshi units (1 BTC = 100,000,000 satoshis)

**Script and Signature Operations**:

- `to_script_pub_key()`: Generates the locking script for an address
- `sign_input()`: Creates a cryptographic signature for a specific input
- `Script()`: Constructs the unlocking script from signature and public key data

### Real Data Analysis and Stack Execution

Let's analyze the actual data from our transaction execution. When this code runs, it produces a real transaction that was broadcast to testnet:

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

Let's break down the unlocking script (ScriptSig) and trace through its execution:

**Unlocking Script (ScriptSig)**:

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

**Locking Script (ScriptPubKey)** from the UTXO being spent:

`76a914c5b28d6bba91a2693a9b1876bcd3929323890fb288ac`

**Parsed Locking Script**:

- `76`: OP_DUP
- `a9`: OP_HASH160
- `14`: OP_PUSHBYTES_20 (push 20 bytes)
- `c5b28d6bba91a2693a9b1876bcd3929323890fb2`: Public key hash (20 bytes)
- `88`: OP_EQUALVERIFY
- `ac`: OP_CHECKSIG

### Stack Execution Trace

Now let's trace through the complete script execution step by step:

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
Verification: c5b28d6b... == c5b28d6b... ✓ (Match!)
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

Verification: ECDSA verification ✓ (Valid signature!)
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

This transaction was successfully broadcast to the Bitcoin testnet and can be viewed at:
[`mempool.space/testnet/tx/bf41b474...a8e58355`](https://mempool.space/testnet/tx/bf41b47481a9d1c99af0b62bb36bc864182312f39a3e1e06c8f6304ba8e58355?showDetails=true)

**Key Observations**:

- The input references UTXO from transaction [`34b90a15...141806f7`](https://mempool.space/testnet/tx/34b90a15d0a9ec9ff3d7bed2536533c73278a9559391cb8c9778b7e7141806f7?showDetails=true) at index 1
- The output sends 29,400 satoshis to a SegWit address
- The transaction fee is 206 satoshis (29,606 - 29,400)
- The signature verification proves ownership of the private key without revealing it

### From P2PKH to Advanced Scripts

P2PKH provides the foundation for understanding Bitcoin's programmable money system, but it's just the beginning. The same principles—stack-based execution, cryptographic verification, and conditional logic—enable more sophisticated scripts that we'll explore in upcoming chapters:

**P2SH (Pay-to-Script-Hash)**:

- Enables complex spending conditions while keeping addresses short
- Moves script complexity from the blockchain to the spender
- Foundation for wrapped SegWit and multi-signature schemes

**P2WPKH (Pay-to-Witness-Public-Key-Hash)**:

- SegWit's equivalent to P2PKH with improved efficiency
- Separates signature data from transaction data
- Reduces transaction malleability and enables Lightning Network

**P2TR (Pay-to-Taproot)**:

- The culmination of Bitcoin's script evolution
- Enables complex smart contracts that look like simple payments
- Combines Schnorr signatures with Merkle trees for maximum flexibility

Each evolution maintains backward compatibility while adding new capabilities. Understanding P2PKH's stack execution model is crucial because Taproot uses the same fundamental approach, just with more sophisticated cryptographic primitives and script structures.

In the next chapter, we'll dive deep into these address types, examining their script structures and understanding how each improvement builds upon the lessons learned from P2PKH.

## Chapter Summary

This chapter established the foundational concepts that make Taproot possible:

**UTXO Model**: Bitcoin represents value as discrete, spendable outputs rather than account balances. Each UTXO must be consumed entirely, creating a cash-like system that enables parallel transaction validation and eliminates complex state management.

**Script System**: Each UTXO contains programmable spending conditions through locking scripts (ScriptPubKey). To spend a UTXO, one must provide an unlocking script (ScriptSig) that satisfies these conditions when executed together.

**Stack Execution**: Bitcoin Script uses a simple stack-based model for processing conditions, where operations manipulate a Last-In-First-Out stack to verify spending authorization.

**P2PKH Implementation**: The fundamental script type demonstrates signature verification and public key validation through a seven-step process: signature and public key provision, duplication, hashing, comparison, and signature verification.

**Practical Development**: Using tools like [`bitcoinutils`](https://github.com/karask/python-bitcoin-utils), developers can construct, sign, and broadcast P2PKH transactions while understanding the underlying cryptographic operations and stack execution.

Understanding these concepts is crucial because Taproot builds upon them, using the same stack-based execution model while introducing new cryptographic primitives and script structures. The journey from simple P2PKH scripts to Taproot's sophisticated spending conditions illustrates Bitcoin's evolution from basic digital cash to a platform for complex financial applications—all while preserving the security and simplicity that make Bitcoin unique.

