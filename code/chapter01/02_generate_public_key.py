"""
Chapter 1 - Example 2: Generating Public Keys

This script demonstrates how to generate Bitcoin public keys in both formats:
- Compressed format (33 bytes)
- Uncompressed format (65 bytes)

Reference: Chapter 1, Section "Compressed vs Uncompressed Public Keys" (lines 124-141)
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey


def main():
    # Setup mainnet (or 'testnet' for test network)
    setup('mainnet')

    # Generate a new Bitcoin private key
    priv = PrivateKey()

    # Get the public key (compressed by default)
    pub = priv.get_public_key()

    # Generate public keys in both formats
    public_key_compressed = pub.to_hex(compressed=True)    # 33 bytes
    public_key_uncompressed = pub.to_hex(compressed=False)  # 65 bytes

    print(f"Compressed:   {public_key_compressed}")
    print(f"Uncompressed: {public_key_uncompressed[:70]}...") 
    # Truncated for display


if __name__ == "__main__":
    main()

