"""
Chapter 2 - Example 1: Building a P2PKH Transaction

This script demonstrates how to build a complete P2PKH transaction:
- Creating transaction inputs and outputs
- Signing a P2PKH input
- Constructing the unlocking script (ScriptSig)
- Serializing the final transaction

Reference: Chapter 2, Section "2.3 Practical Implementation: Building a P2PKH transaction" (lines 268-328)
"""

from bitcoinutils.setup import setup
from bitcoinutils.utils import to_satoshis
from bitcoinutils.transactions import Transaction, TxInput, TxOutput
from bitcoinutils.keys import P2wpkhAddress, P2pkhAddress, PrivateKey
from bitcoinutils.script import Script


def main():
    # Setup testnet environment
    setup('testnet')

    # Sender information - Legacy P2PKH
    # NOTE: This is a TESTNET private key used for educational purposes only.
    # The key is intentionally exposed here for reproducibility of the example.
    # NEVER use this key or any exposed private key for real Bitcoin transactions.
    private_key = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
    public_key = private_key.get_public_key()
    from_address_str = "myYHJtG3cyoRseuTwvViGHgP2efAvZkYa4"
    from_address = P2pkhAddress(from_address_str)

    # Receiver - SegWit address
    to_address = P2wpkhAddress('tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4')

    print(f"Sender Legacy Address: {from_address_str}")
    print(f"Receiver SegWit Address: {to_address.to_string()}")

    # Create transaction input (referencing previous UTXO)
    txin = TxInput(
        '34b90a15d0a9ec9ff3d7bed2536533c73278a9559391cb8c9778b7e7141806f7',
        1  # vout index
    )

    # Calculate amounts
    total_input = 0.00029606  # Input amount in BTC
    amount_to_send = 0.00029400  # Amount to send
    fee = total_input - amount_to_send  # Transaction fee

    # Create transaction output
    txout = TxOutput(to_satoshis(amount_to_send), to_address.to_script_pub_key())

    # Create unsigned transaction
    tx = Transaction([txin], [txout])

    print(f"Unsigned transaction: {tx.serialize()}")

    # Get the P2PKH locking script for signing
    p2pkh_script = from_address.to_script_pub_key()

    # Sign the transaction input
    signature = private_key.sign_input(tx, 1, p2pkh_script) ##Is the tx index here supposed to be 1 like the above in the txin section?

    # Create the unlocking script: <signature> <public_key>
    txin.script_sig = Script([signature, public_key.to_hex()])

    # Get the signed transaction
    signed_tx = tx.serialize()

    print(f"Signed transaction: {signed_tx}")
    print(f"Transaction size: {tx.get_size()} bytes")


if __name__ == "__main__":
    main()

