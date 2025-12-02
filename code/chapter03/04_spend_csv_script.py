"""
Chapter 3 - Example 4: Spending a CSV Time-Locked P2SH UTXO

This script demonstrates how to spend a CSV time-locked P2SH UTXO:
- Setting the sequence number in the transaction input
- Waiting for the required number of blocks
- Providing signature and redeem script

Reference: Chapter 3, Section "3.3 Time-Locked Inheritance: CSV-Enhanced P2SH" (lines 357-372)
"""

from bitcoinutils.setup import setup
from bitcoinutils.utils import to_satoshis
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, Sequence
from bitcoinutils.keys import PrivateKey, P2pkhAddress
from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK
from bitcoinutils.script import Script


def spend_csv_script():
    """Spend a CSV time-locked P2SH UTXO"""
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
    
    utxo_txid = '34f5bf0cf328d77059b5674e71442ded8cdcfc723d0136733e0dbf180861906f'
    utxo_vout = 0
    recipient_address = P2pkhAddress('myYHJtG3cyoRseuTwvViGHgP2efAvZkYa4')
    
    txin = TxInput(utxo_txid, utxo_vout, sequence=seq.for_input_sequence())
    txout = TxOutput(to_satoshis(0.00001), recipient_address.to_script_pub_key())
    tx = Transaction([txin], [txout])
    
    sig = private_key.sign_input(tx, 0, redeem_script)
    txin.script_sig = Script([
        sig,
        public_key.to_hex(),
        redeem_script.to_hex()
    ])
    
    signed_tx = tx.serialize()
    
    print(f"Sequence value: {seq.for_input_sequence()}")
    print(f"Signed transaction: {signed_tx}")
    print(f"Transaction size: {tx.get_size()} bytes")
    
    return signed_tx


if __name__ == "__main__":
    spend_csv_script()

