"""
Chapter 3 - Example 2: Spending a Multi-signature P2SH UTXO

This script demonstrates how to spend a multi-signature P2SH UTXO:
- Creating a transaction with P2SH input
- Signing with multiple private keys (2-of-3)
- Constructing the ScriptSig with signatures and redeem script

Reference: Chapter 3, Section "3.2 Multi-signature Treasury: 2-of-3 Corporate Security" (lines 119-142)
"""

from bitcoinutils.setup import setup
from bitcoinutils.utils import to_satoshis
from bitcoinutils.transactions import Transaction, TxInput, TxOutput
from bitcoinutils.keys import PrivateKey, P2pkhAddress
from bitcoinutils.script import Script


def spend_multisig_p2sh():
    """Spend a 2-of-3 multi-signature P2SH UTXO"""
    setup('testnet')
    
    # Private keys for Alice and Bob (2-of-3)
    # These must match the keys used in create_multisig_p2sh.py
    alice_sk = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
    bob_sk = PrivateKey('cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG')
    
    # Public keys (same as in create_multisig_p2sh)
    alice_pk = '02898711e6bf63f5cbe1b38c05e89d6c391c59e9f8f695da44bf3d20ca674c8519'
    bob_pk = '0284b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5'
    carol_pk = '0317aa89b43f46a0c0cdbd9a302f2508337ba6a06d123854481b52de9c20996011'
    
    # Recreate the redeem script (must match the one used to create the P2SH address)
    redeem_script = Script([
        'OP_2',
        alice_pk,
        bob_pk,
        carol_pk,
        'OP_3',
        'OP_CHECKMULTISIG'
    ])
    
    # Previous UTXO details
    utxo_txid = '4b869865bc4a156d7e0ba14590b5c8971e57b8198af64d88872558ca88a8ba5f'
    utxo_vout = 0
    utxo_amount = 0.00001600  # 1,600 satoshis
    
    # Recipient address (example)
    recipient_address = P2pkhAddress('myYHJtG3cyoRseuTwvViGHgP2efAvZkYa4')
    
    # Create transaction
    txin = TxInput(utxo_txid, utxo_vout)
    txout = TxOutput(to_satoshis(0.00000888), recipient_address.to_script_pub_key())
    tx = Transaction([txin], [txout])
    
    # Sign with Alice and Bob's keys
    alice_sig = alice_sk.sign_input(tx, 0, redeem_script)
    bob_sig = bob_sk.sign_input(tx, 0, redeem_script)
    
    # Construct ScriptSig: OP_0 <sig1> <sig2> <redeem_script>
    # OP_0 is required due to OP_CHECKMULTISIG bug
    txin.script_sig = Script([
        'OP_0',                    # OP_CHECKMULTISIG bug workaround
        alice_sig,                 # First signature
        bob_sig,                   # Second signature  
        redeem_script.to_hex()     # Reveal the redeem script
    ])
    
    # Get the signed transaction
    signed_tx = tx.serialize()
    
    print(f"Signed transaction: {signed_tx}")
    print(f"Transaction size: {tx.get_size()} bytes")
    
    return signed_tx


if __name__ == "__main__":
    spend_multisig_p2sh()

