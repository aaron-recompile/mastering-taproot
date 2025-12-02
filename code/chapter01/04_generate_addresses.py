"""
Chapter 1 - Example 4: Generating Different Address Types

This script demonstrates how to generate different Bitcoin address types
from the same key pair:
- Legacy (P2PKH): Base58Check encoded, prefix "1"
- SegWit Native (P2WPKH): Bech32 encoded, prefix "bc1q"
- SegWit P2SH (P2SH-P2WPKH): Base58Check encoded, prefix "3"
- Taproot (P2TR): Bech32m encoded, prefix "bc1p"

Reference: Chapter 1, Section "Address Generation: From Public Keys to Payment Destinations" (lines 183-206)
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from bitcoinutils.script import Script
from bitcoinutils.keys import P2shAddress, P2wpkhAddress


def main():
    # Setup mainnet (or 'testnet' for test network)
    setup('mainnet')

    # Generate a new Bitcoin private key
    priv = PrivateKey()

    # Get the public key
    pub = priv.get_public_key()

    # Generate different address types from the same key
    legacy_address = pub.get_address()                    # P2PKH
    segwit_native = pub.get_segwit_address()              # P2WPKH
    taproot_address = pub.get_taproot_address()          # P2TR
    
    # For P2SH-P2WPKH, we need to wrap the P2WPKH script in a P2SH
    segwit_script = segwit_native.to_script_pub_key()
    segwit_p2sh = P2shAddress.from_script(segwit_script)  # P2SH-P2WPKH

    print(f"Legacy (P2PKH):     {legacy_address.to_string()}")
    print(f"SegWit Native:      {segwit_native.to_string()}")
    print(f"SegWit P2SH:        {segwit_p2sh.to_string()}")
    print(f"Taproot:            {taproot_address.to_string()}")


if __name__ == "__main__":
    main()

