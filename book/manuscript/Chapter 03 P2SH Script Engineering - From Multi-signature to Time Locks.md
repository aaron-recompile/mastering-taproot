# Chapter 3: P2SH Script Engineering - From Multi-signature to Time Locks

Pay-to-Script-Hash (P2SH) is where Bitcoin scripting first becomes practical: any script, however complex, can be locked behind a single 20-byte hash and revealed only when the funds are spent. This chapter uses P2SH to build the two patterns that recur through the rest of the book — multisignature and time locks — and traces both through the stack. It sits between the single-signature P2PKH of Chapter 2 and the script trees of Taproot.

## 3.1 P2SH Architecture: Scripts Behind the Hash

P2SH lets any script be represented by a compact 20-byte hash, moving the script's complexity out of the UTXO set and deferring it to spending time.

### The Two-Stage Verification Model

P2SH operates through two distinct phases:

**Stage 1: Hash Verification**

```
OP_HASH160 <script_hash> OP_EQUAL
```

**Stage 2: Script Execution**

```
<revealed_script> -> Execute as Bitcoin Script
```

### P2SH Address Generation Process

P2SH follows the same Hash160 -> Base58Check pattern covered in Chapter 1, but hashes the script instead of a public key:

```
Script Serialization -> hex_encoded_script
Hash160(script)     -> 20_bytes_script_hash  
Version + Base58Check -> 3...address (mainnet)
```

All P2SH addresses begin with "3" on mainnet and "2" on testnet, immediately distinguishing them from P2PKH addresses.

### ScriptSig Construction Pattern

The unlocking script (ScriptSig) for P2SH follows a specific pattern:

```
<script_data> <serialized_redeem_script>
```

Where `<script_data>` contains the values needed to satisfy the redeem script's conditions, and `<serialized_redeem_script>` is the original script whose hash matches the locking script.

## 3.2 2-of-3 Multisig

A multisig output needs more than one key to spend. A 2-of-3 scheme — any two of three keys — is the common shape for shared custody: no single person can move the funds alone, and no single lost key locks them away either.

### The Setup: Three Keys

Three parties each hold a key, and any two of them can authorize a spend:

- **Alice**, **Bob**, and **Carol** — three keys, two required.

The redeem script encodes that rule with Bitcoin's `OP_CHECKMULTISIG` opcode:

```python
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from bitcoinutils.script import Script
from bitcoinutils.keys import P2shAddress

def create_multisig_p2sh():
    setup('testnet')
    
    # Stakeholder public keys
    alice_pk = '02898711e6bf63f5cbe1b38c05e89d6c391c59e9f8f695da44bf3d20ca674c8519'
    bob_pk = '0284b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5'
    carol_pk = '0317aa89b43f46a0c0cdbd9a302f2508337ba6a06d123854481b52de9c20996011'
    
    # 2-of-3 multisig redeem script
    redeem_script = Script([
        'OP_2',           # Require 2 signatures
        alice_pk,         # Alice's public key
        bob_pk,           # Bob's public key  
        carol_pk,         # Carol's public key
        'OP_3',           # Total of 3 keys
        'OP_CHECKMULTISIG' # Multisig verification
    ])
    
    # Generate P2SH address
    p2sh_addr = P2shAddress.from_script(redeem_script)
    return p2sh_addr, redeem_script
```

### bitcoinutils Function Analysis

**`Script([...])` Constructor**: Creates a Script object from a list of opcodes and data. The library automatically handles the encoding of opcodes like `'OP_2'` into their byte representations (`0x52`).

**`P2shAddress.from_script(script)`**: Generates a P2SH address by:
1. Serializing the script to bytes
2. Computing Hash160(script) 
3. Adding version byte (0x05 for mainnet, 0xc4 for testnet)
4. Applying Base58Check encoding

**Script Serialization**: The redeem script serializes to:

```text
522102898711e6bf63f5cbe1b38c05e89d6c391c59e9f8f695da44bf3d20ca674c8519
210284b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5
210317aa89b43f46a0c0cdbd9a302f2508337ba6a06d123854481b52de9c20996011
53ae
```

Breaking this down:
- `52`: OP_2
- `21`: Push 33 bytes (compressed public key)
- `02898711...`: Alice's public key
- `21`: Push 33 bytes  
- `0284b595...`: Bob's public key
- `21`: Push 33 bytes
- `0317aa89...`: Carol's public key
- `53`: OP_3
- `ae`: OP_CHECKMULTISIG

### Spending the Multi-signature UTXO

When Alice and Bob decide to authorize a payment, they must provide their signatures in the correct order along with the redeem script:

```python
def spend_multisig_p2sh():
    # Previous UTXO details
    utxo_txid = '4b869865bc4a156d7e0ba14590b5c8971e57b8198af64d88872558ca88a8ba5f'
    utxo_vout = 0
    utxo_amount = 0.00001600  # 1,600 satoshis
    
    # Create transaction
    txin = TxInput(utxo_txid, utxo_vout)
    txout = TxOutput(to_satoshis(0.00000888), recipient_address.to_script_pub_key())
    tx = Transaction([txin], [txout])
    
    # Sign with Alice and Bob's keys
    alice_sig = alice_sk.sign_input(tx, 0, redeem_script)
    bob_sig = bob_sk.sign_input(tx, 0, redeem_script)
    
    # Construct ScriptSig
    txin.script_sig = Script([
        'OP_0',                    # OP_CHECKMULTISIG bug workaround
        alice_sig,                 # First signature
        bob_sig,                   # Second signature  
        redeem_script.to_hex()     # Reveal the redeem script
    ])
```

### bitcoinutils Signature Functions

**`private_key.sign_input(tx, input_index, script)`**: Creates an ECDSA signature for a specific transaction input using the provided script for the signature hash calculation. The script parameter should be the redeem script for P2SH inputs.

**`script.to_hex()`**: Serializes the Script object into its hexadecimal byte representation, which is pushed as data onto the stack during script execution.

### Multi-signature Stack Execution Analysis

Let's trace through the complete script execution using our real transaction data, following Bitcoin Core's two-phase P2SH execution:

**Transaction ID**: [`e68bef53...ba0fd4e0`](https://mempool.space/testnet/tx/e68bef534c7536300c3ae5ccd0f79e031cab29d262380a37269151e8ba0fd4e0?showDetails=true)

### Phase 1: ScriptSig + ScriptPubKey Execution

**Initial State:**

```
│ (empty)                                │
└────────────────────────────────────────┘
```

### 1. PUSH OP_0: Multisig bug workaround
Bitcoin's OP_CHECKMULTISIG has a known off-by-one bug that pops an extra item from the stack. An OP_0 is pushed to compensate.

```
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

### 2. PUSH Alice's Signature: First authorization

```
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

### 3. PUSH Bob's Signature: Second authorization  

```
│ 3044022065f8...fd9e01 (bob_sig)        │
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

### 4. PUSH Redeem Script: Reveal the spending conditions

```
│ 522102898711...601153ae (redeem_script)  │
│ 3044022065f8...fd9e01 (bob_sig)          │
│ 30440220694f...7a6501 (alice_sig)        │
│ 00 (op_zero)                             │
└──────────────────────────────────────────┘
```

### 5. OP_HASH160: Verify script hash matches
The P2SH locking script `OP_HASH160 <script_hash> OP_EQUAL` is executed:

```
│ dd81b5beb3d8...5cb0ca (computed_hash)    │
│ 3044022065f8...fd9e01 (bob_sig)          │
│ 30440220694f...7a6501 (alice_sig)        │
│ 00 (op_zero)                             │
└──────────────────────────────────────────┘
```

### 6. PUSH Expected Hash: From locking script

```
│ dd81b5beb3d8...5cb0ca (expected_hash)    │
│ dd81b5beb3d8...5cb0ca (computed_hash)    │
│ 3044022065f8...fd9e01 (bob_sig)          │
│ 30440220694f...7a6501 (alice_sig)        │
│ 00 (op_zero)                             │
└──────────────────────────────────────────┘
```

### 7. OP_EQUAL: Confirm hash match

```
│ 1 (true)                               │
│ 3044022065f8...fd9e01 (bob_sig)        │
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

**(Phase 1 complete: Hash verification successful)**

### P2SH Transition: Stack Reset Mechanism

**Critical Point**: Bitcoin Core recognizes the P2SH pattern and transitions to a second validation phase by:

1. **Detects P2SH pattern**: `OP_HASH160 <hash> OP_EQUAL` 
2. **Resets stack**: Back to post-scriptSig state (discards TRUE)
3. **Extracts redeem script**: From original scriptSig data
4. **Prepares clean execution**: For redeem script with signature data

**Stack Reset to Post-ScriptSig State:**

```
│ 3044022065f8...fd9e01 (bob_sig)        │
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

**(TRUE is discarded - redeem script begins with clean stack)**

### Phase 2: Redeem Script Execution

Bitcoin Core now executes the redeem script: `OP_2 alice_pk bob_pk carol_pk OP_3 OP_CHECKMULTISIG`

### 8. OP_2: Push required signature count

```
│ 2 (required_sigs)                      │
│ 3044022065f8...fd9e01 (bob_sig)        │
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

### 9-11. PUSH Public Keys: Load verification keys

```
│ 0317aa89b43f...996011 (carol_pk)       │
│ 0284b5951609...eef63af5 (bob_pk)       │
│ 02898711e6bf...674c8519 (alice_pk)     │
│ 2 (required_sigs)                      │
│ 3044022065f8...fd9e01 (bob_sig)        │
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

### 12. OP_3: Push total key count

```
│ 3 (total_keys)                         │
│ 0317aa89b43f...996011 (carol_pk)       │
│ 0284b5951609...eef63af5 (bob_pk)       │
│ 02898711e6bf...674c8519 (alice_pk)     │
│ 2 (required_sigs)                      │
│ 3044022065f8...fd9e01 (bob_sig)        │
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

### 13. OP_CHECKMULTISIG: Verify signatures
The opcode consumes:
- Key count (3)
- Public keys (Alice, Bob, Carol)  
- Signature count (2)
- Signatures (Alice's, Bob's)
- Extra item (OP_0, due to bug)

Verification process:
1. Alice's signature verified against Alice's public key [OK]
2. Bob's signature verified against Bob's public key [OK]
3. Required threshold (2-of-3) satisfied [OK]

### Final State: Multisig Verification Complete

```
│ 1 (true)                               │
└────────────────────────────────────────┘
```

**(P2SH execution successful: Clean two-phase verification)**

## 3.3 Time Locks with CSV

CheckSequenceVerify (CSV) enforces a relative time lock: spending is delayed by a number of blocks counted from when the UTXO was created. Below is a real testnet implementation.

### A 3-Block Time Lock

**Transaction ID**: [`34f5bf0c...0861906f`](https://mempool.space/testnet/tx/34f5bf0cf328d77059b5674e71442ded8cdcfc723d0136733e0dbf180861906f?showDetails=true)

This transaction combines a CSV time lock with a P2PKH signature check in one redeem script — the shape used for inheritance and escrow conditions.

### CSV Script Construction

The time lock is a simple linear script, no branching:

```python
from bitcoinutils.setup import setup
from bitcoinutils.transactions import Sequence
from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK

def create_csv_script():
    setup('testnet')
    
    # 3-block relative time lock
    relative_blocks = 3
    seq = Sequence(TYPE_RELATIVE_TIMELOCK, relative_blocks)
    
    # Combined CSV + P2PKH script
    redeem_script = Script([
        seq.for_script(),           # Push 3
        'OP_CHECKSEQUENCEVERIFY',   # Verify time lock
        'OP_DROP',                  # Remove delay value
        'OP_DUP',                   # Standard P2PKH starts here
        'OP_HASH160',
        p2pkh_addr.to_hash160(),
        'OP_EQUALVERIFY', 
        'OP_CHECKSIG'
    ])
    
    return redeem_script
```

### bitcoinutils CSV Functions

**`Sequence(TYPE_RELATIVE_TIMELOCK, blocks)`**: Creates a sequence object for relative block-based delays. The sequence value encodes the time constraint that will be enforced by OP_CHECKSEQUENCEVERIFY.

**`seq.for_script()`**: Returns the sequence value formatted for use in script opcodes (pushes the delay value onto the stack).

**`seq.for_input_sequence()`**: Returns the sequence value for the transaction input's sequence field, which CSV validates against.

### Spending the Time-Locked UTXO

```python
def spend_csv_script():
    # Must wait 3 blocks after UTXO creation
    seq = Sequence(TYPE_RELATIVE_TIMELOCK, 3)
    
    # Set sequence in transaction input
    txin = TxInput(utxo_txid, utxo_vout, sequence=seq.for_input_sequence())
    
    # Provide signature and redeem script
    sig = private_key.sign_input(tx, 0, redeem_script)
    txin.script_sig = Script([
        sig,                        # Signature for P2PKH
        public_key.to_hex(),        # Public key for P2PKH  
        redeem_script.to_hex()      # Reveal the script
    ])
```

### CSV Stack Execution Analysis

Let's trace through the execution using real transaction data from our testnet example:

**ScriptSig Data**:
- Signature: `30440220...` (71 bytes)
- Public Key: `0250be5f...6bb4d3` (33 bytes)  
- Redeem Script: `53b27576a9145cdc...88ac` (28 bytes)

### Phase 1: P2SH Hash Verification

**(Stack reset mechanism applies - see multisig section for details)**

### Phase 2: CSV + P2PKH Execution

**Initial State** (after P2SH reset):

```
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

### 1. PUSH 3: Time delay requirement

```
│ 3 (delay_blocks)                       │
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

### 2. OP_CHECKSEQUENCEVERIFY: Verify time lock
CSV validates that the transaction input's sequence number >= 3:

```
│ 3 (delay_blocks)                       │
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

**(Verification: nSequence >= 3 blocks since UTXO creation)**

### 3. OP_DROP: Remove delay value

```
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

### 4. OP_DUP: Begin P2PKH verification

```
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

### 5. OP_HASH160: Hash public key

```
│ 5cdc28d6b1876...cabaadcc (pubkey_hash) │
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

### 6. PUSH Expected Hash: From redeem script

```
│ 5cdc28d6b1876...cabaadcc (expected_hash) │
│ 5cdc28d6b1876...cabaadcc (computed_hash) │
│ 0250be5fc44ec...4d3 (pubkey)             │
│ 30440220a1b2...c3d401 (signature)        │
└──────────────────────────────────────────┘
```

### 7. OP_EQUALVERIFY: Confirm hash match

```
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

### 8. OP_CHECKSIG: Final signature verification

```
│ 1 (true)                               │
└────────────────────────────────────────┘
```

**(Time lock satisfied and signature verified - CSV spending successful)**

### Time Lock Error Handling

**Common Error: `non-BIP68-final`**

If you attempt to spend before the time lock expires:

```python
# This will fail if fewer than 3 blocks have passed
response = requests.post(mempool_api, data=signed_tx)
# Returns: "non-BIP68-final"
```

The transaction is rejected because `nSequence < required_delay`, violating the CSV constraint.

### Where CSV Is Used

- **Inheritance**: funds become spendable by an heir after a set period of owner inactivity.
- **Escrow**: a fallback path opens after a delay if the primary condition isn't met.
- **Payment channels**: Lightning uses CSV to enforce settlement delays, which is what gives each party a window to dispute an old state.

## 3.4 P2SH vs P2PKH: What P2SH Adds, and Where It Stops

P2SH extends Bitcoin Script from single-signature authorization to multi-party and time-based conditions, while keeping the same compact address format. But it has a limit that motivates everything Taproot does next.

When a P2SH output is spent, the *entire* redeem script is revealed — every branch, whether or not it was taken. There's no way to expose only the relevant path. So the structure is linear and fully visible: every signature path, time-lock clause, and fallback condition ends up on chain. And because the redeem script rides in the scriptSig, multisig and inheritance setups carry real size overhead, which means higher fees.

Taproot addresses both directly: complex scripts stay hidden until needed, committed into a tree where only the executed path is ever revealed. That is the thread the next chapters pick up.

## Chapter Summary

P2SH locks a script behind its hash and reveals it only at spending time. We built the two patterns that recur for the rest of the book:

- **Multisig** — `OP_CHECKMULTISIG` with a 2-of-3 redeem script, plus the `OP_0` workaround for its off-by-one bug.
- **Time locks** — `OP_CHECKSEQUENCEVERIFY` for a relative delay, combined with a P2PKH check.

We traced both on the stack, including P2SH's two-phase execution: verify the script's hash, then reset the stack and run the revealed script.

One limitation matters most for what follows: P2SH reveals the *entire* redeem script when spent, every branch included. Taproot's answer to exactly that — revealing only the branch you use — is what the rest of the book builds toward.

**Next.** Chapter 4 turns to SegWit: moving the witness out of the transaction body, which fixes malleability and sets up Taproot's witness-based spending paths.
