"""
Chapter 1 - Example 3: Taproot X-Only Public Keys

This script demonstrates how to extract x-only public keys for Taproot.
Taproot uses x-only public keys (32 bytes), which only contain the x-coordinate
without the y-coordinate parity information.

Reference: Chapter 1, Section "X-Only Public Keys: Taproot's Innovation" (lines 153-158)
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey


def main():
    # Setup mainnet (or 'testnet' for test network)
    setup('mainnet')

    # Generate a new Bitcoin private key
    priv = PrivateKey()

    # Get the public key
    pub = priv.get_public_key()

    # Taproot uses x-only public keys (32 bytes)
    # Get the x-coordinate only
    taproot_pubkey = pub.to_x_only_hex()  # 32 bytes, x-coordinate only
    print(f"X-only Public Key: {taproot_pubkey}")


if __name__ == "__main__":
    main()

