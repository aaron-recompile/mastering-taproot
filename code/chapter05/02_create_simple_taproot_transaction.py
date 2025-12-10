"""
Create Simple Taproot Transaction - Putting It All Together

This script demonstrates creating a basic Taproot-to-Taproot transaction:
- Taproot address generation
- Transaction construction with SegWit enabled
- Schnorr signature creation (64-byte fixed size)
- Minimal witness structure (only signature, no public key)
- Transaction size and efficiency analysis

Reference: Chapter 5, Section "Simple Taproot Transaction: Putting It All Together" (lines 283-367)
"""

from bitcoinutils.setup import setup
from bitcoinutils.utils import to_satoshis
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.keys import PrivateKey, P2trAddress

def create_simple_taproot_transaction():
    """Creates a basic Taproot-to-Taproot transaction"""
    setup('testnet')
    
    # Sender's information
    from_private_key = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
    from_pub = from_private_key.get_public_key()
    from_address = from_pub.get_taproot_address()
    
    # Receiver's address
    to_address = P2trAddress('tb1p53ncq9ytax924ps66z6al3wfhy6a29w8h6xfu27xem06t98zkmvsakd43h')
    
    print("=== TAPROOT TRANSACTION CREATION ===")
    print(f"From Address: {from_address.to_string()}")
    print(f"To Address: {to_address.to_string()}")
    
    print(f"\n=== TRANSACTION SETUP ===")
    print(f"Sender Private Key: {from_private_key.to_wif()}")
    print(f"Sender Public Key:  {from_pub.to_hex()}")
    print(f"From Address (P2TR): {from_address.to_string()}")
    print(f"To Address (P2TR):   {to_address.to_string()}")
    
    # Create transaction input
    prev_txid = 'b0f49d2f30f80678c6053af09f0611420aacf20105598330cb3f0ccb8ac7d7f0'
    prev_vout = 0
    txin = TxInput(prev_txid, prev_vout)
    
    print(f"\n=== INPUT DETAILS ===")
    print(f"Previous TXID: {prev_txid}")
    print(f"VOUT: {prev_vout}")
    
    # Input amount and script for signing
    input_amount = 0.00029200
    amounts = [to_satoshis(input_amount)]
    input_script = from_address.to_script_pub_key()
    scripts = [input_script]
    
    print(f"Input Amount: {input_amount} BTC ({to_satoshis(input_amount)} satoshis)")
    print(f"Input ScriptPubKey: {input_script.to_hex()}")
    print(f"  Format: OP_1 <32-byte-output-key> (Taproot)")
    
    # Create transaction output
    amount_to_send = 0.00029000
    txout = TxOutput(
        to_satoshis(amount_to_send),
        to_address.to_script_pub_key()
    )
    
    print(f"\n=== OUTPUT DETAILS ===")
    print(f"Output Amount: {amount_to_send} BTC ({to_satoshis(amount_to_send)} satoshis)")
    print(f"Output ScriptPubKey: {to_address.to_script_pub_key().to_hex()}")
    print(f"  Format: OP_1 <32-byte-output-key> (Taproot)")
    print(f"Fee: {input_amount - amount_to_send} BTC ({to_satoshis(input_amount - amount_to_send)} satoshis)")
    
    # Create transaction with SegWit enabled
    tx = Transaction([txin], [txout], has_segwit=True)
    
    print(f"\n=== UNSIGNED TRANSACTION ===")
    unsigned_tx = tx.serialize()
    print(f"Hex: {unsigned_tx}")
    print(f"TxId: {tx.get_txid()}")
    print(f"Size: {len(unsigned_tx) // 2} bytes")
    
    # Sign the transaction using Schnorr signature
    # The sign_taproot_input() API handles the complex sighash construction:
    # 1. Builds BIP341 sighash with all input amounts and scripts
    # 2. Creates the signature message: sighash + key_version + code_separator
    # 3. Generates 64-byte Schnorr signature using tweaked private key
    print(f"\n=== SIGNING PROCESS ===")
    print(f"Signing with Schnorr signature (BIP340)...")
    print(f"  - Building BIP341 sighash with input amounts and scripts")
    print(f"  - Creating signature message: sighash + key_version + code_separator")
    print(f"  - Generating 64-byte Schnorr signature using tweaked private key")
    
    sig = from_private_key.sign_taproot_input(
        tx,
        0,
        scripts,
        amounts
    )
    
    print(f"\n=== SIGNATURE DETAILS ===")
    sig_bytes = len(sig) // 2  # Hex string length / 2 = bytes
    print(f"Signature Length: {sig_bytes} bytes (hex: {len(sig)} chars)")
    print(f"Signature (hex): {sig}")
    print(f"  r-value: {sig[:64]} (32 bytes)")
    print(f"  s-value: {sig[64:]} (32 bytes)")
    print(f"  Total: {sig_bytes} bytes (fixed size, no variable encoding)")
    print(f"  Note: This is a BIP340 Schnorr signature (64 bytes)")
    
    # Add witness data - the simplification here reflects Taproot's efficiency
    # Unlike SegWit's [signature, public_key], Taproot needs only [signature]
    # The public key is embedded in the scriptPubKey as the output key
    print(f"\n=== WITNESS CONSTRUCTION ===")
    print(f"Taproot Witness Structure:")
    print(f"  - Unlike SegWit P2WPKH: [signature, public_key]")
    print(f"  - Taproot P2TR: [signature] only")
    print(f"  - Public key is embedded in scriptPubKey as output key")
    print(f"  - Witness items: 1 (just the signature)")
    
    tx.witnesses.append(TxWitnessInput([sig]))
    
    # Get signed transaction
    signed_tx = tx.serialize()
    
    print(f"\n=== SIGNED TRANSACTION ===")
    print(f"Hex: {signed_tx}")
    print(f"Size: {len(signed_tx) // 2} bytes")
    print(f"Virtual Size: {tx.get_vsize()} vbytes")
    
    print(f"\n=== TRANSACTION SUMMARY ===")
    print(f"Send Amount: {amount_to_send} BTC ({to_satoshis(amount_to_send)} satoshis)")
    print(f"Fee: {input_amount - amount_to_send} BTC ({to_satoshis(input_amount - amount_to_send)} satoshis)")
    print(f"Transaction Size: {tx.get_size()} bytes")
    print(f"Virtual Size: {tx.get_vsize()} vbytes")
    
    print(f"\nKey Observations:")
    print(f"1. Taproot Address Generation: get_taproot_address() automatically applies the tweaking process")
    print(f"2. Schnorr Signing: sign_taproot_input() produces exactly 64-byte signatures")
    print(f"3. Minimal Witness: Only the signature is needed in the witness stack")
    print(f"   (In practice the item is 64 or 65 bytes: with SIGHASH_DEFAULT the 1-byte flag is omitted;")
    print(f"    for other sighashes the flag byte is appended)")
    print(f"4. Identical Appearance: This transaction looks identical to any other Taproot transaction")
    
    return tx, sig


if __name__ == "__main__":
    tx, signature = create_simple_taproot_transaction()
    
    print("\n" + "=" * 60)
    print("TAPROOT EFFICIENCY COMPARISON")
    print("=" * 60)
    print("Legacy P2PKH:")
    print("  - ScriptPubKey: OP_DUP OP_HASH160 <20-byte-hash> OP_EQUALVERIFY OP_CHECKSIG")
    print("  - ScriptSig: <signature> <public_key>")
    print("  - Size: ~225 bytes")
    print("  - Information Revealed: Single signature spending")
    print("\nSegWit P2WPKH:")
    print("  - ScriptPubKey: OP_0 <20-byte-hash>")
    print("  - Witness: [signature, public_key]")
    print("  - Size: ~165 bytes")
    print("  - Information Revealed: Single signature spending")
    print("\nTaproot P2TR:")
    print("  - ScriptPubKey: OP_1 <32-byte-output-key>")
    print("  - Witness: [schnorr_signature]")
    print("  - Size: ~135 bytes")
    print("  - Information Revealed: Nothing about internal complexity")
    print("\n🔮 The Magic: Simple and complex Taproot transactions are")
    print("   completely indistinguishable until spent!")

