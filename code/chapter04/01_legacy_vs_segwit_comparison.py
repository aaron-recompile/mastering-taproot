"""
Legacy P2PKH vs SegWit P2WPKH Transaction Signing Comparison

This script demonstrates the key differences between legacy and SegWit transaction signing:
- Legacy: Signature goes in scriptSig
- SegWit: Signature goes in witness, scriptSig remains empty

Reference: Chapter 4, Section 4.1
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey, P2pkhAddress, P2wpkhAddress
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.script import Script
from bitcoinutils.utils import to_satoshis

def legacy_p2pkh_signing():
    """Demonstrates legacy P2PKH transaction signing"""
    print("=" * 60)
    print("LEGACY P2PKH SIGNING")
    print("=" * 60)
    
    setup('testnet')
    
    private_key_wif = 'cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT'
    sk = PrivateKey(private_key_wif)
    from_addr = P2pkhAddress(sk.get_public_key().get_address().to_string())
    
    print(f"Private Key (WIF): {private_key_wif}")
    print(f"From Address: {from_addr.to_string()}")
    
    previous_locking_script = Script([
        "OP_DUP",
        "OP_HASH160", 
        from_addr.to_hash160(),
        "OP_EQUALVERIFY",
        "OP_CHECKSIG"
    ])
    
    print(f"\nPrevious Locking Script: {previous_locking_script.to_hex()}")
    
    txin = TxInput('5e4a294028ea8cb0e156dac36f4444e2c445c7b393e87301b12818b06cee49e0', 0)
    txout = TxOutput(to_satoshis(0.00000866), P2pkhAddress('myYHJtG3cyoRseuTwvViGHgP2efAvZkYa4').to_script_pub_key())
    tx = Transaction([txin], [txout])
    
    sig = sk.sign_input(tx, 0, previous_locking_script)
    pk = sk.get_public_key().to_hex()
    unlocking_script = Script([sig, pk])
    txin.script_sig = unlocking_script
    
    print(f"\nUnlocking Script (scriptSig): {txin.script_sig.to_hex()}")
    print(f"Signature: {sig[:20]}...{sig[-10:]}")
    print(f"Public Key: {pk}")
    print(f"\n✓ Signature goes in scriptSig (included in TXID)")
    
    return tx


def segwit_p2wpkh_signing():
    """Demonstrates SegWit P2WPKH transaction signing"""
    print("\n" + "=" * 60)
    print("SEGWIT P2WPKH SIGNING")
    print("=" * 60)
    
    setup('testnet')
    
    private_key = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
    public_key = private_key.get_public_key()
    from_address = public_key.get_segwit_address()
    
    print(f"Private Key (WIF): {private_key.to_wif()}")
    print(f"From Address: {from_address.to_string()}")
    
    # Real UTXO from testnet (same as in 02_create_segwit_transaction.py)
    utxo_txid = '1454438e6f417d710333fbab118058e2972127bdd790134ab74937fa9dddbc48'
    utxo_vout = 0
    utxo_amount = 1000  # sats
    
    txin = TxInput(utxo_txid, utxo_vout)
    to_address = P2wpkhAddress('tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4')
    txout = TxOutput(to_satoshis(0.00000666), to_address.to_script_pub_key())
    
    # CRITICAL: has_segwit=True required for SegWit
    tx = Transaction([txin], [txout], has_segwit=True)
    
    # CRITICAL: Use sign_segwit_input with script_code from public key's address
    script_code = public_key.get_address().to_script_pub_key()
    signature = private_key.sign_segwit_input(
        tx,
        0,
        script_code,
        to_satoshis(utxo_amount / 100000000)
    )
    
    # CRITICAL: ScriptSig must be empty for SegWit
    txin.script_sig = Script([])
    
    # CRITICAL: Use TxWitnessInput wrapper
    tx.witnesses.append(TxWitnessInput([signature, public_key.to_hex()]))
    
    print(f"\nScriptSig: '{txin.script_sig.to_hex() if txin.script_sig else ''}'")
    witness_count = len([signature, public_key.to_hex()]) if tx.witnesses else 0
    print(f"Witness Items: {witness_count}")
    print(f"  [0] Signature: {signature[:20]}...{signature[-10:]}")
    print(f"  [1] Public Key: {public_key.to_hex()}")
    print(f"\n✓ Signature goes in witness (NOT in TXID)")
    print(f"✓ ScriptSig remains empty")
    print(f"✓ Used sign_segwit_input (not sign_input)")
    print(f"✓ Script code from public key's legacy address")
    
    return tx


if __name__ == "__main__":
    legacy_tx = legacy_p2pkh_signing()
    segwit_tx = segwit_p2wpkh_signing()
    
    print("\n" + "=" * 60)
    print("KEY DIFFERENCES")
    print("=" * 60)
    print("Legacy:")
    print("  - Signature in scriptSig")
    print("  - scriptSig included in TXID calculation")
    print("  - Vulnerable to transaction malleability")
    print("\nSegWit:")
    print("  - Signature in witness")
    print("  - scriptSig empty (00)")
    print("  - Witness excluded from TXID calculation")
    print("  - Malleability resistant")

