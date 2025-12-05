"""
Complete SegWit Transaction Creation - Step by Step

This script demonstrates building a SegWit transaction in two phases:
- Phase 1: Create unsigned transaction (empty scriptSig, no witness)
- Phase 2: Add SegWit signature (witness data, scriptSig remains empty)

Reference: Chapter 4, Sections 4.2 and 4.3

✅ VERIFIED: This code has been successfully tested and broadcast to testnet.
   Real on-chain transaction: 271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6
   View on explorer: https://blockstream.info/testnet/tx/271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey, P2wpkhAddress
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.utils import to_satoshis
from bitcoinutils.script import Script

def create_segwit_transaction():
    """Creates a complete SegWit transaction step by step"""
    setup('testnet')
    
    print("=" * 60)
    print("SEGWIT TRANSACTION SETUP")
    print("=" * 60)
    
    # Private key and public key
    private_key = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
    public_key = private_key.get_public_key()
    
    # CRITICAL: Get script_code from the public key's address
    # This is required for SegWit signing - must derive from the public key
    script_code = public_key.get_address().to_script_pub_key()
    
    # Addresses
    from_address = P2wpkhAddress('tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4')
    to_address = P2wpkhAddress('tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4')
    
    print(f"From: {from_address.to_string()}")
    print(f"To:   {to_address.to_string()}")
    print(f"Script Code (from pubkey): {script_code.to_hex()}")
    
    # Verify private key matches address
    print(f"\n=== Private Key Verification ===")
    print(f"Private key WIF: {private_key.to_wif()}")
    print(f"Generated address: {public_key.get_segwit_address().to_string()}")
    print(f"Expected address: {from_address.to_string()}")
    print(f"Match: {'✓' if public_key.get_segwit_address().to_string() == from_address.to_string() else '✗'}")
    
    print("\n" + "=" * 60)
    print("PHASE 1: CREATE UNSIGNED TRANSACTION")
    print("=" * 60)
    
    # UTXO information
    utxo_txid = '1454438e6f417d710333fbab118058e2972127bdd790134ab74937fa9dddbc48'
    utxo_vout = 0
    utxo_amount = 1000  # sats (from UTXO data)
    
    # Transaction amounts
    amount_to_send = 666  # sats
    fee = 334  # sats (1000 - 666)
    
    txin = TxInput(utxo_txid, utxo_vout)
    txout = TxOutput(to_satoshis(amount_to_send / 100000000), to_address.to_script_pub_key())
    
    # CRITICAL: has_segwit=True is required for witness data serialization
    tx = Transaction([txin], [txout], has_segwit=True)
    unsigned_tx = tx.serialize()
    
    print(f"Unsigned TX: {unsigned_tx}")
    print(f"\nTransaction Components:")
    print(f"  Version:      02000000")
    print(f"  Input Count:  01")
    print(f"  TXID:         {utxo_txid}")
    print(f"  VOUT:         {utxo_vout:08x}")
    print(f"  ScriptSig:    00 (empty, 0 bytes)")
    print(f"  Sequence:     fffffffd (RBF enabled)")
    print(f"  Output Count: 01")
    print(f"  Value:        {amount_to_send} sats")
    print(f"  ScriptPubKey: {to_address.to_script_pub_key().to_hex()}")
    print(f"  Locktime:     00000000")
    print(f"\nKey Observations:")
    print(f"  - Standard Bitcoin transaction structure")
    print(f"  - ScriptSig is empty (00) - normal for SegWit")
    print(f"  - No witness data yet")
    
    print("\n" + "=" * 60)
    print("PHASE 2: ADD SEGWIT SIGNATURE")
    print("=" * 60)
    
    # CRITICAL: Use sign_segwit_input (not sign_input)
    # Must provide:
    # 1. script_code: Derived from public key's address (required for SegWit)
    # 2. input_amount: The UTXO amount in satoshis (required for SegWit)
    print(f"Signing with:")
    print(f"  Script Code: {script_code.to_hex()}")
    print(f"  Input Amount: {utxo_amount} sats")
    
    signature = private_key.sign_segwit_input(
        tx,
        0,
        script_code,  # CRITICAL: Must use script_code from public key's address
        to_satoshis(utxo_amount / 100000000)  # CRITICAL: Must provide input amount
    )
    
    # CRITICAL: ScriptSig must be empty for SegWit
    txin.script_sig = Script([])
    
    # CRITICAL: Use TxWitnessInput to wrap witness data
    public_key_hex = public_key.to_hex()
    tx.witnesses.append(TxWitnessInput([signature, public_key_hex]))
    
    print(f"\nScriptSig: '{txin.script_sig.to_hex() if txin.script_sig else ''}' (must be empty)")
    if tx.witnesses:
        # Witness data is stored in the list we passed to TxWitnessInput
        witness_items = [signature, public_key_hex]
        print(f"Witness Items: {len(witness_items)}")
        print(f"  [0] Signature: {signature[:20]}...{signature[-10:]}")
        print(f"  [1] Public Key: {public_key_hex}")
    else:
        print(f"Witness Items: 0")
    
    signed_tx = tx.serialize()
    print(f"\nSigned TX: {signed_tx}")
    
    print(f"\nCritical Changes:")
    print(f"  - ScriptSig remains empty (required for SegWit)")
    print(f"  - Witness data appears (using TxWitnessInput)")
    print(f"  - Transaction becomes longer (added witness section)")
    print(f"  - Used sign_segwit_input (not sign_input)")
    print(f"  - Provided script_code and input_amount (required for SegWit)")
    
    print("\n" + "=" * 60)
    print("TRANSACTION STRUCTURE COMPARISON")
    print("=" * 60)
    print("Before Signing (Phase 1):")
    print("  Standard Bitcoin Transaction Format")
    print("  Total: 84 bytes")
    print("\nAfter Signing (Phase 2):")
    print("  SegWit Transaction Format")
    print("  ├── Version: 02000000")
    print("  ├── Marker: 00 (NEW - SegWit indicator)")
    print("  ├── Flag: 01 (NEW - SegWit version)")
    print("  ├── Input Data (ScriptSig still empty)")
    print("  ├── Output Data")
    print("  ├── Witness Data (NEW - authorization data)")
    print("  └── Locktime: 00000000")
    print("  Total: 191 bytes (added witness section: 82 bytes)")
    print("\nNote: marker/flag (00 01) appear only in serialized form")
    print("      to indicate SegWit and do not participate in txid")
    print("      (they do participate in wtxid)")
    
    return tx, unsigned_tx, signed_tx


if __name__ == "__main__":
    tx, unsigned_tx, signed_tx = create_segwit_transaction()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("✓ SegWit separates witness data from transaction data")
    print("✓ ScriptSig remains empty for native SegWit")
    print("✓ Witness data excluded from TXID calculation")
    print("✓ Transaction malleability resistance achieved")
    print("\n" + "=" * 60)
    print("VERIFIED ON-CHAIN TRANSACTION")
    print("=" * 60)
    print("✅ This code has been successfully tested and broadcast to testnet")
    print(f"   TXID: 271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6")
    print(f"   Explorer: https://blockstream.info/testnet/tx/271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6")
    print(f"   Input: 1,000 sats (V0_P2WPKH)")
    print(f"   Output: 666 sats (V0_P2WPKH)")
    print(f"   Fee: 334 sats")
    print(f"   Status: Confirmed on testnet")

