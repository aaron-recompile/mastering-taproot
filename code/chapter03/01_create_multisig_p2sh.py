"""
Chapter 3 - Example 1: Creating a Multi-signature P2SH Address

This script demonstrates how to create a 2-of-3 multi-signature P2SH address:
- Constructing a multi-signature redeem script
- Generating a P2SH address from the redeem script
- Understanding the script serialization process

Reference: Chapter 3, Section "3.2 Multi-signature Treasury: 2-of-3 Corporate Security" (lines 62-89)
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from bitcoinutils.script import Script
from bitcoinutils.keys import P2shAddress


def create_multisig_p2sh():
    """Create a 2-of-3 multi-signature P2SH address"""
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
    
    print(f"Redeem Script: {redeem_script.to_hex()}")
    print(f"P2SH Address: {p2sh_addr.to_string()}")
    
    return p2sh_addr, redeem_script


if __name__ == "__main__":
    create_multisig_p2sh()
