# Chapter 1: Private Keys, Public Keys, and Address Encoding

Understanding Bitcoin's cryptographic foundation is essential before diving into Taproot's advanced features. This chapter covers the fundamentals of private keys, public keys, and address generation—the building blocks that make Bitcoin transactions possible.

## The Cryptographic Hierarchy

Bitcoin's security model relies on a one-way mathematical relationship between private keys, public keys, and addresses:

```
Private Key (256-bit) → Public Key (ECDSA point) → Address (encoded hash)

```

Each step in this hierarchy serves a specific purpose:

- **Private keys** provide cryptographic ownership and signing capability
- **Public keys** enable signature verification and payment authorization
- **Addresses** offer a user-friendly way to receive payments while preserving privacy

## Private Keys: The Foundation of Ownership

A Bitcoin private key is fundamentally a 256-bit random number—a massive integer that serves as the secret foundation of cryptocurrency ownership. To put this in perspective, the total number of possible private keys (2^256) is comparable to the estimated number of atoms in the observable universe.

### Generating Private Keys

Let's start with a practical example using Python's `bitcoinlib`:

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

The hexadecimal representation contains exactly 64 characters (each representing 4 bits), totaling 256 bits or 32 bytes. This format is mathematically precise but not human-friendly for storage or import/export operations.

### Wallet Import Format (WIF)

The Wallet Import Format (WIF) addresses the usability challenges of raw hexadecimal private keys by applying Base58Check encoding. This encoding:

- Adds error detection through checksums
- Eliminates visually confusing characters (0, O, I, l)
- Provides a standardized format for wallet import/export

The WIF encoding process follows these steps:

1. **Add version prefix**: `0x80` for mainnet, `0xEF` for testnet
2. **(Optional) Add compression flag**: If the corresponding public key will be compressed, append `0x01` to the payload. This step changes the final Base58 prefix of the WIF
2. **Calculate checksum**: Apply SHA256(SHA256(data)) and take first 4 bytes
3. **Apply Base58 encoding**: Convert to human-readable format

![WIF encoding flow](./resources/wif-encoding-flow.png)


*Figure 1-1: WIF encoding transforms a 32-byte private key into a Base58Check encoded string*

The resulting WIF strings have distinctive prefixes:

- **L** or **K**: Mainnet private keys
- **c**: Testnet private keys

## Public Keys: Cryptographic Verification Points

Public keys in Bitcoin are points on the secp256k1 elliptic curve, derived from private keys through elliptic curve multiplication. While the mathematical details involve complex curve arithmetic, the practical implementation is straightforward.

### ECDSA and secp256k1

Bitcoin uses the secp256k1 curve for its elliptic curve digital signature algorithm (ECDSA). The secp256k1 curve is defined by the equation:

```
y² = x³ + 7

```

![Secp256k1 curve](./resources/Secp256k1.png)

*Figure 1-2: The secp256k1 elliptic curve used by Bitcoin*

Without diving into the mathematical complexities, understand that:

- Each private key `k` generates a unique point `(x, y)` on the curve
- This relationship is computationally irreversible
- The curve's properties ensure cryptographic security

### Compressed vs Uncompressed Public Keys

Public keys can be represented in two formats:

**Uncompressed Format (65 bytes):**

```
04 + x-coordinate (32 bytes) + y-coordinate (32 bytes)

```

**Compressed Format (33 bytes):**

```
02/03 + x-coordinate (32 bytes)

```

The compression works because the elliptic curve's mathematical properties allow reconstructing the y-coordinate from the x-coordinate, knowing only whether y is even or odd:

- `02` prefix: y-coordinate is even
- `03` prefix: y-coordinate is odd

```python
# Generate public keys in both formats
public_key_compressed = key.public_hex          # 33 bytes
public_key_uncompressed = key.public_uncompressed_hex  # 65 bytes

print(f"Compressed:   {public_key_compressed}")
print(f"Uncompressed: {public_key_uncompressed}") 

```

**Example output:**

```
Compressed:   0250be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3
Uncompressed: 0450be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d36dbc816fe21ba41dfa6e6a92d0ccd62240b8a9eaa87d508b2ee330ef03162a90

```

Modern Bitcoin implementations exclusively use compressed public keys due to their smaller size and equivalent security.

### X-Only Public Keys: Taproot's Innovation

Taproot introduces **x-only public keys**, using only the x-coordinate without the y-coordinate parity information. This 32-byte format:

- Reduces transaction sizes
- Simplifies signature verification
- Enables key aggregation techniques

```python
# Taproot uses x-only public keys (32 bytes)
taproot_pubkey = key.public_hex[2:]  # Remove the 02/03 prefix
print(f"X-only Public Key: {taproot_pubkey}")

```

This innovation plays a crucial role in Taproot's efficiency improvements, which we'll explore in detail in later chapters.

## Address Generation: From Public Keys to Payment Destinations

Bitcoin addresses are **not** public keys—they are encoded hashes of public keys. This additional layer provides:

- **Privacy**: Addresses don't directly reveal public keys
- **Quantum resistance**: Hash functions provide post-quantum security
- **Error detection**: Encoding includes checksums

### The Address Generation Process

All Bitcoin addresses follow a similar pattern:

1. **Hash the public key**: Apply SHA256 followed by RIPEMD160（or Hash160)
2. **Add metadata**: Version bytes and script type information
3. **Add checksum**: Error detection mechanism
4. **Encode**: Base58Check or Bech32 encoding

![Legacy bitcoin address flow](./resources/Bitcoin_address_legacy.png)

*Figure 1-3: Converting a public key to a Bitcoin address through hashing and encoding in a Legacy way*

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
Legacy (P2PKH):     1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
SegWit Native:      bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kygt080
SegWit P2SH:        3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy
Taproot:            bc1plz0h3rlj2zvn88pgywqtr9k3df3p75p3ltuxh0

```

## Address Types and Encoding Formats

### Base58Check Encoding

Base58Check encoding, used for legacy addresses, eliminates visually similar characters and includes error detection:

**Excluded characters:** `0` (zero), `O` (capital o), `I` (capital i), `l` (lowercase L)

**P2PKH (Pay-to-Public-Key-Hash):**

- Prefix: `1`
- Format: Base58Check encoded
- Usage: Original Bitcoin address format
- Example: `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa`

**P2SH (Pay-to-Script-Hash):**

- Prefix: `3`
- Format: Base58Check encoded
- Usage: Multi-signature and wrapped SegWit addresses
- Example: `3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy`

### Bech32 Encoding: SegWit's Innovation

Bech32 encoding, introduced with SegWit, provides superior error detection and correction capabilities:

**P2WPKH (Pay-to-Witness-Public-Key-Hash):**

- Prefix: `bc1q`
- Format: Bech32 encoded
- Benefits: Lower fees, better error detection
- Example: `bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kygt080`

### Bech32m Encoding: Taproot's Enhancement

Taproot addresses use Bech32m, an improved version of Bech32:

**P2TR (Pay-to-Taproot):**

- Prefix: `bc1p`
- Format: Bech32m encoded
- Benefits: Enhanced privacy, script flexibility
- Example: `bc1plz0h3rlj2zvn88pgywqtr9k3df3p75p3ltuxh0`

## Address Format Comparison

| Address Type | Encoding | Data Size | Address Length | Prefix | Primary Use Case |
| --- | --- | --- | --- | --- | --- |
| **P2PKH** | Base58Check | 25 bytes | ~34 chars | `1...` | Legacy payments |
| **P2SH** | Base58Check | 25 bytes | ~34 chars | `3...` | Multi-sig, wrapped SegWit |
| **P2WPKH** | Bech32 | 21 bytes | 42-46 chars | `bc1q...` | SegWit payments |
| **P2TR** | Bech32m | 33 bytes | 58-62 chars | `bc1p...` | Taproot payments |

While address encoding involves many subtle rules—like version bytes, checksums, and different encodings (Base58Check, Bech32, Bech32m)—it’s more important to understand the general idea:

👉 addresses are for humans. They’re just a user-friendly representation of locking scripts (scriptPubKey), not a required component of the protocol itself.

Once you recognize the prefix (1, 3, bc1q, bc1p), you already know what kind of script is behind it.From the node’s perspective, Bitcoin never stores addresses—only scripts.


In later chapters, we’ll focus on what truly matters: the actual scriptPubKey associated with each address type. That’s where the real logic lives—and where Bitcoin’s scripting and programmability begin. If you can predict the script behind the address, you can reason about how it’s spent.


## The Derivation Model

Understanding the derivation relationships between keys and addresses is crucial. The diagram below brings together the entire address derivation pipeline—from private key generation to the final on-chain script. While most wallet users only see the address, developers need to trace the full path to understand how Bitcoin enforces ownership and spending conditions.

![Key-pubkey-address relationships](./resources/TheDerivationModel.png)

*Figure 1-4: The derivation relationships between private keys, public keys, addresses, and WIF format*

```
Private Key (k)
    ↓ ECDSA multiplication
Public Key (x, y)
    ↓ SHA256 + RIPEMD160
Public Key Hash (20 bytes)
    ↓ Version + Checksum + Encoding
Address (Base58/Bech32)
  ↓ Decoded by wallet/node
ScriptPubKey (locking script on-chain)
```

**Security properties:**

- **Forward derivation**: Each step is computationally easy
- **Reverse derivation**: Each step is computationally infeasible
- **Hash collision resistance**: Extremely unlikely for different public keys to produce the same address


## Practical Implications for Taproot

As we'll see in subsequent chapters, Taproot builds upon these foundational concepts:

- **X-only public keys** reduce transaction size and enable key aggregation
- **Bech32m encoding** provides robust error detection for complex scripts
- **Unified address format** makes multisig and single-sig transactions indistinguishable

Understanding these encoding and key formats prepares us for Taproot's more sophisticated features, where multiple spending conditions can be elegantly combined into a single address format.

## Chapter Summary

This chapter established the cryptographic foundation for Bitcoin transactions:

- Private keys are 256-bit random numbers encoded in WIF format for usability
- Public keys are elliptic curve points, with compressed format being standard
- Addresses are encoded hashes of public keys, not the public keys themselves
- Different address types use different encoding schemes: Base58Check, Bech32, and Bech32m
- Taproot introduces x-only public keys and Bech32m encoding for enhanced efficiency

All the components introduced here—keys, hashes, encodings—are what Bitcoin Script ultimately manipulates or validates.In the next chapter, we'll explore how these keys and addresses interact with Bitcoin Script—the programming language that defines spending conditions and enables Taproot's advanced capabilities.
