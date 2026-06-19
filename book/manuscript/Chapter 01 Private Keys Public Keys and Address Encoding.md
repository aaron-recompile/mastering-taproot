# Chapter 1: Private Keys, Public Keys, and Address Encoding

Every Bitcoin spend traces back to one chain of derivations: a private key produces a public key, and a public key produces an address. This chapter walks that chain end to end — generate a key, encode it, and turn it into the four address formats you will meet through the rest of the book. None of it is Taproot-specific yet, but the two pieces introduced at the end — x-only public keys and Bech32m — are exactly what Taproot is built on.

## 1.1 The Derivation Chain

Bitcoin's ownership model is a one-way chain. Each arrow is cheap to compute forwards and infeasible to run backwards:

```text
Private Key (256-bit) -> Public Key (ECDSA point) -> Address (encoded hash)

```

The three pieces divide the work cleanly: the private key signs, the public key lets anyone verify that signature, and the address is the short string you hand out to receive funds — with the public key itself kept out of sight until the moment you spend.

## 1.2 Private Keys: The Foundation of Ownership

A Bitcoin private key is just a 256-bit number — a random integer drawn from a space of 2^256. That space is the entire security argument: it is on the order of the estimated number of atoms in the observable universe, so guessing someone else's key is not a strategy anyone can mount.

### Generating Private Keys

Start with Python's `bitcoinlib`:

```python
from bitcoinlib.keys import Key

# Generate a new Bitcoin key pair
key = Key()

# Extract the private key in different formats
private_key_hex = key.private_hex      # 32 bytes (256-bit) in hexadecimal
private_key_wif = key.wif()           # Wallet Import Format

print(f"Private Key (HEX): {private_key_hex}")
print(f"Private Key (WIF): {private_key_wif}")

```

**Example output:**

```
Private Key (HEX): e9873d79c6d87dc0fb6a5778633389dfa5c32fa27f99b5199abf2f9848ee0289
Private Key (WIF): L1aW4aubDFB7yfras2S1mN3bqg9w3KmCPSM3Qh4rQG9E1e84n5Bd

```

The hex form is exactly 64 characters — 256 bits, 32 bytes — and it is what the math actually operates on. It is also unforgiving: mistype one character and you get a different, perfectly valid-looking key with no warning. WIF exists to close that gap.

### Wallet Import Format (WIF)

WIF wraps the raw key in Base58Check. That wrapping adds a checksum so a typo is caught before it costs you anything, drops the visually ambiguous characters (`0`, `O`, `I`, `l`), and gives every wallet one standard string to import and export.

The encoding runs in four steps:

1. **Add a version prefix**: `0x80` for mainnet, `0xEF` for testnet.
2. **(Optional) Add a compression flag**: if the matching public key will be compressed, append `0x01` to the payload. This single byte is what changes the final Base58 prefix of the WIF.
3. **Calculate the checksum**: take `SHA256(SHA256(data))` and keep the first 4 bytes.
4. **Base58-encode** the result into the human-readable string.

![WIF encoding flow](./resources/wif-encoding-flow.png)


*Figure 1-1: WIF encoding transforms a 32-byte private key into a Base58Check encoded string*

The prefix tells you what you are holding at a glance:

- **L** or **K**: mainnet private key (compressed)
- **c**: testnet private key

## 1.3 Public Keys: Cryptographic Verification Points

A public key is a point on the secp256k1 elliptic curve, obtained by multiplying the private key into the curve's fixed base point. The arithmetic behind that multiplication is what makes the step irreversible; in code it is a single attribute access.

### ECDSA and secp256k1

Bitcoin signs with ECDSA over the secp256k1 curve, defined by:

```
y^2 = x^3 + 7

```

![Secp256k1 curve](./resources/Secp256k1.png)

*Figure 1-2: The secp256k1 elliptic curve used by Bitcoin*

For everything in this book, two properties are enough: every private key `k` maps to exactly one point `(x, y)` on the curve, and that map cannot be run in reverse.

### Compressed vs Uncompressed Public Keys

A public key can be written two ways.

**Uncompressed (65 bytes):**

```
04 + x-coordinate (32 bytes) + y-coordinate (32 bytes)

```

**Compressed (33 bytes):**

```
02/03 + x-coordinate (32 bytes)

```

Compression works because the curve equation lets you recover `y` from `x` alone, once you know whether `y` is even or odd — and that single bit rides in the prefix:

- `02`: y is even
- `03`: y is odd

```python
# Generate public keys in both formats
public_key_compressed = key.public_hex          # 33 bytes
public_key_uncompressed = key.public_uncompressed_hex  # 65 bytes

print(f"Compressed:   {public_key_compressed}")
print(f"Uncompressed: {public_key_uncompressed}") 

```

**Example output:**

```
Compressed:   0250be5f...d126bb4d3
Uncompressed: 0450be5f...03162a90

```

Everything modern uses the compressed form: half the bytes, identical security.

### X-Only Public Keys: Taproot's Innovation

Taproot drops the prefix entirely and works with **x-only public keys** — the bare 32-byte x-coordinate. The parity byte disappears because Taproot fixes the convention (a key is always taken with even `y`), which trims a byte off every key and is what lets Schnorr key aggregation stay clean. From Chapter 5 onward, this is the format in play.

```python
# Taproot uses x-only public keys (32 bytes)
taproot_pubkey = key.public_hex[2:]  # Remove the 02/03 prefix
print(f"X-only Public Key: {taproot_pubkey}")

```

## 1.4 Address Generation: From Public Keys to Payment Destinations

A Bitcoin address is **not** a public key. It is an encoded hash of one, and that extra hashing step buys three things at once:

- **Privacy**: the public key stays hidden until you spend.
- **A hedge against the curve breaking**: a hash sits in front of the elliptic-curve key, so a future weakness in secp256k1 does not immediately expose unspent funds.
- **Error detection**: the encoding carries a checksum.

### The Address Generation Process

Every Bitcoin address is built the same way:

1. **Hash the public key**: SHA256 followed by RIPEMD160 (together, Hash160).
2. **Add metadata**: version bytes and script-type information.
3. **Add a checksum**: the error-detection bytes.
4. **Encode**: Base58Check or Bech32 / Bech32m.

![Legacy bitcoin address flow](./resources/Bitcoin_address_legacy.png)

*Figure 1-3: Converting a public key to a Bitcoin address through hashing and encoding in the Legacy way*

```python
# Generate different address types from the same key
legacy_address = key.address()                          # P2PKH
segwit_native = key.address(encoding='bech32')          # P2WPKH
segwit_p2sh = key.address(encoding='base58', script_type='p2sh')  # P2SH-P2WPKH
taproot_address = key.address(script_type='p2tr')       # P2TR

print(f"Legacy (P2PKH):     {legacy_address}")
print(f"SegWit Native:      {segwit_native}")
print(f"SegWit P2SH:        {segwit_p2sh}")
print(f"Taproot:            {taproot_address}")

```

**Example output:**

```
Legacy (P2PKH):     18hJWrx86tQJr5wtnvPPvPGyLcZh1iWv3f
SegWit Native:      bc1q235z8005az3sd7yvwptcx4fcvnylg6t5a0k9mz
SegWit P2SH:        3HG3QEzpBSJ8qJFZFxYZ2MF5GcBgjhjan8
Taproot:            bc1p75g5xj09v30jh604nhhaff83ph268tz30lyycrkujx589p9yj3vqdr74ns

```

## 1.5 Address Types and Encoding Formats

### Base58Check Encoding

Base58Check, used for legacy addresses, drops visually similar characters and folds in a checksum.

**Excluded characters:** `0` (zero), `O` (capital o), `I` (capital i), `l` (lowercase L)

**P2PKH (Pay-to-Public-Key-Hash):**

- Prefix: `1`
- Format: Base58Check encoded
- Usage: the original Bitcoin address format
- Example: `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa`

**P2SH (Pay-to-Script-Hash):**

- Prefix: `3`
- Format: Base58Check encoded
- Usage: multi-signature and wrapped SegWit addresses
- Example: `3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy`

### Bech32 Encoding: SegWit's Innovation

Bech32, introduced with SegWit, not only detects common typos but can often point at which character is wrong.

**P2WPKH (Pay-to-Witness-Public-Key-Hash):**

- Prefix: `bc1q`
- Format: Bech32 encoded
- Benefits: lower fees, stronger error detection
- Example: `bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kygt080`

### Bech32m Encoding: Taproot's Enhancement

Taproot addresses use Bech32m, a tweaked Bech32 that fixes an edge case in the original checksum.

**P2TR (Pay-to-Taproot):**

- Prefix: `bc1p`
- Format: Bech32m encoded
- Benefits: key-path and script-path spends share one address format
- Example: `bc1p75g5xj...vqdr74ns` (62 chars; full address in §1.4 output)

## 1.6 Address Format Comparison

| Address Type | Encoding | Data Size | Address Length | Prefix | Primary Use Case |
| --- | --- | --- | --- | --- | --- |
| **P2PKH** | Base58Check | 25 bytes | ~34 chars | `1...` | Legacy payments |
| **P2SH** | Base58Check | 25 bytes | ~34 chars | `3...` | Multi-sig, wrapped SegWit |
| **P2WPKH** | Bech32 | 21 bytes | 42-46 chars | `bc1q...` | SegWit payments |
| **P2TR** | Bech32m | 33 bytes | 58-62 chars | `bc1p...` | Taproot payments |

Address encoding has plenty of fiddly rules — version bytes, checksums, three different schemes — but the idea underneath is simpler than the rules suggest:

Addresses are for humans. They are a user-friendly stand-in for a locking script (scriptPubKey), not a part of the protocol itself. Once you recognize the prefix (`1`, `3`, `bc1q`, `bc1p`), you already know which script sits behind it. From the node's point of view, Bitcoin never stores addresses — only scripts.

Later chapters keep their attention on that script — the actual scriptPubKey behind each address type. That is where the real logic lives, and where Bitcoin's programmability begins. If you can predict the script behind an address, you can reason about how it is spent.

## 1.7 The Derivation Model

One diagram ties the whole chain together — from generating a key down to the script that actually lands on-chain. Wallet users only ever see the address; as a developer you need the full path, because that path is what the node enforces.

![Key-pubkey-address relationships](./resources/TheDerivationModel.png)

*Figure 1-4: The derivation relationships between private keys, public keys, addresses, and WIF format*

```
Private Key (k)
    v ECDSA multiplication
Public Key (x, y)
    v SHA256 + RIPEMD160
Public Key Hash (20 bytes)
    v Version + Checksum + Encoding
Address (Base58/Bech32)
    v Decoded by wallet/node
ScriptPubKey (locking script on-chain)
```

The chain is asymmetric by design:

- **Forward**: each step is cheap to compute.
- **Reverse**: each step is computationally infeasible.
- **Collision resistance**: two different public keys producing the same address is vanishingly unlikely.

## 1.8 What Carries Into Taproot

Three things from this chapter resurface the moment Taproot appears: **x-only public keys** (Chapter 5), **Bech32m** as the address format for P2TR, and the idea that an address is only ever a stand-in for a locking script. Hold onto that last point in particular — from here on the interesting question is never "what is the address" but "what script is behind it, and how is it spent." Chapter 2 starts answering that by introducing Bitcoin Script itself.
