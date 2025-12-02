"""
Chapter 3 - Example 3: Creating a CSV Time-Locked P2SH Script

This script demonstrates how to create a P2SH script with CheckSequenceVerify (CSV):
- Creating a relative time lock (3 blocks)
- Combining CSV with P2PKH signature verification
- Generating a P2SH address from the time-locked script

Reference: Chapter 3, Section "3.3 Time-Locked Inheritance: CSV-Enhanced P2SH" (lines 320-345)
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey, P2pkhAddress
from bitcoinutils.transactions import Sequence
from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK
from bitcoinutils.script import Script
from bitcoinutils.keys import P2shAddress


def create_csv_script():
    """Create a CSV time-locked P2SH script (3 blocks delay)"""
    setup('testnet')
    
    private_key = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    public_key = private_key.get_public_key()
    p2pkh_addr = public_key.get_address()
    
    relative_blocks = 3
    seq = Sequence(TYPE_RELATIVE_TIMELOCK, relative_blocks)
    
    redeem_script = Script([
        seq.for_script(),
        'OP_CHECKSEQUENCEVERIFY',
        'OP_DROP',
        'OP_DUP',
        'OP_HASH160',
        p2pkh_addr.to_hash160(),
        'OP_EQUALVERIFY', 
        'OP_CHECKSIG'
    ])
    
    p2sh_addr = P2shAddress.from_script(redeem_script)
    
    print(f"Public Key: {public_key.to_hex()}")
    print(f"P2PKH Address: {p2pkh_addr.to_string()}")
    print(f"Redeem Script: {redeem_script.to_hex()}")
    print(f"P2SH Address: {p2sh_addr.to_string()}")
    print(f"Time Lock: {relative_blocks} blocks")
    
    return p2sh_addr, redeem_script, private_key, public_key


if __name__ == "__main__":
    create_csv_script()

