"""
Chapter 1 - Example 1: Generating Private Keys

This script demonstrates how to generate Bitcoin private keys in different formats:
- Hexadecimal format (32 bytes, 256-bit)
- Wallet Import Format (WIF)

Reference: Chapter 1, Section "Generating Private Keys" (lines 24-49)
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey


def main():
    # Setup mainnet (or 'testnet' for test network)
    setup('mainnet')

    # Generate a new Bitcoin private key
    priv = PrivateKey()

    # Extract the private key in different formats
    private_key_hex = priv.to_bytes().hex()  # 32 bytes (256-bit) in hexadecimal
    private_key_wif = priv.to_wif()          # Wallet Import Format

    print(f"Private Key (HEX): {private_key_hex}")
    print(f"Private Key (WIF): {private_key_wif}")


if __name__ == "__main__":
    main()

