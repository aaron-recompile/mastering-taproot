"""
Chapter 1 - Example 5: Verify Address Formats and Sizes

This script verifies the generated addresses:
- Checks address lengths and formats
- Verifies byte sizes of underlying data
- Explains why Taproot addresses are longer

Reference: Chapter 1, Address format comparison
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from bitcoinutils.script import Script
from bitcoinutils.keys import P2shAddress, P2wpkhAddress
import base58


def verify_address(address_obj, address_str, address_type):
    """Verify address format and extract information"""
    print(f"\n{address_type}:")
    print(f"  Address: {address_str}")
    print(f"  Length: {len(address_str)} characters")
    
    # Get the scriptPubKey to see the underlying data
    script_pubkey = address_obj.to_script_pub_key()
    script_hex = script_pubkey.to_hex()
    script_bytes = bytes.fromhex(script_hex)
    
    if address_str[0] == '1' or address_str[0] == '3':
        # Base58Check encoded (P2PKH or P2SH)
        try:
            decoded = base58.b58decode(address_str)
            # Base58Check: version byte (1) + hash (20 bytes) + checksum (4 bytes) = 25 bytes
            print(f"  Format: Base58Check")
            print(f"  Decoded bytes: {len(decoded)} bytes")
            print(f"  Version byte: 0x{decoded[0]:02x}")
            print(f"  Hash160: {decoded[1:21].hex()} ({len(decoded[1:21])} bytes)")
            print(f"  Checksum: {decoded[21:].hex()} ({len(decoded[21:])} bytes)")
            print(f"  ScriptPubKey: {script_hex} ({len(script_bytes)} bytes)")
        except Exception as e:
            print(f"  Error decoding: {e}")
    
    elif address_str.startswith('bc1q'):
        # Bech32 encoded (P2WPKH)
        print(f"  Format: Bech32 (SegWit v0)")
        print(f"  ScriptPubKey: {script_hex} ({len(script_bytes)} bytes)")
        # P2WPKH script: OP_0 (0x00) + pushdata (0x14 = 20) + hash160 (20 bytes) = 22 bytes
        if len(script_bytes) == 22 and script_bytes[0] == 0x00 and script_bytes[1] == 0x14:
            print(f"  ✓ Correct format: OP_0 + pushdata(20) + 20-byte hash160")
            print(f"  Version: 0x00 (P2WPKH)")
            print(f"  Hash160: {script_bytes[2:].hex()} ({len(script_bytes[2:])} bytes)")
        else:
            print(f"  ⚠ Unexpected script format")
    
    elif address_str.startswith('bc1p'):
        # Bech32m encoded (P2TR)
        print(f"  Format: Bech32m (SegWit v1 / Taproot)")
        print(f"  ScriptPubKey: {script_hex} ({len(script_bytes)} bytes)")
        # P2TR script: OP_1 (0x51) + pushdata (0x20 = 32) + x-only pubkey (32 bytes) = 34 bytes
        if len(script_bytes) == 34 and script_bytes[0] == 0x51 and script_bytes[1] == 0x20:
            print(f"  ✓ Correct format: OP_1 + pushdata(32) + 32-byte x-only pubkey")
            print(f"  Version: 0x01 (P2TR)")
            print(f"  X-only pubkey: {script_bytes[2:].hex()} ({len(script_bytes[2:])} bytes)")
            print(f"  Note: Taproot addresses are longer because:")
            print(f"        - They use 32-byte x-only pubkeys (vs 20-byte hashes)")
            print(f"        - Bech32m encoding overhead")
            print(f"        - But provide better privacy and script flexibility")
        else:
            print(f"  ⚠ Unexpected script format")


def main():
    # Setup mainnet
    setup('mainnet')

    # Generate a new Bitcoin private key
    priv = PrivateKey()
    pub = priv.get_public_key()

    # Generate different address types
    legacy_address = pub.get_address()
    segwit_native = pub.get_segwit_address()
    taproot_address = pub.get_taproot_address()
    
    # For P2SH-P2WPKH
    segwit_script = segwit_native.to_script_pub_key()
    segwit_p2sh = P2shAddress.from_script(segwit_script)

    print("=" * 70)
    print("Bitcoin Address Format Verification")
    print("=" * 70)
    
    verify_address(legacy_address, legacy_address.to_string(), "Legacy (P2PKH)")
    verify_address(segwit_native, segwit_native.to_string(), "SegWit Native (P2WPKH)")
    verify_address(segwit_p2sh, segwit_p2sh.to_string(), "SegWit P2SH (P2SH-P2WPKH)")
    verify_address(taproot_address, taproot_address.to_string(), "Taproot (P2TR)")
    
    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    print("P2PKH:      ~34 chars (Base58Check, 20-byte hash160)")
    print("P2WPKH:     ~42-46 chars (Bech32, 20-byte hash160)")
    print("P2SH-P2WPKH: ~34 chars (Base58Check, 20-byte script hash)")
    print("P2TR:       ~58-62 chars (Bech32m, 32-byte x-only pubkey)")
    print("\nTaproot addresses are longer because:")
    print("  - They use 32-byte x-only public keys (not 20-byte hashes)")
    print("  - Bech32m encoding is slightly less efficient than Base58Check")
    print("  - But they provide better privacy and script flexibility")


if __name__ == "__main__":
    main()

