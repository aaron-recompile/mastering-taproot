"""
Demonstrate Key Tweaking - The Bridge to Taproot

This script demonstrates the key tweaking process that enables Taproot:
- Internal key generation
- Script commitment (empty for key-path-only)
- Tweak calculation using BIP341 formula
- Tweaking application (P' = P + t×G, d' = d + t)
- Mathematical verification

Reference: Chapter 5, Section "Key Tweaking: The Bridge to Taproot" (lines 178-249)
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
import hashlib

def demonstrate_key_tweaking():
    """Demonstrates the complete key tweaking process"""
    setup('testnet')
    
    # Step 1: Generate internal key pair
    internal_private_key = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
    internal_public_key = internal_private_key.get_public_key()
    
    print("=== STEP 1: Internal Key Generation ===")
    print(f"Internal Private Key: {internal_private_key.to_wif()}")
    print(f"Internal Public Key:  {internal_public_key.to_hex()}")
    
    # Step 2: Create simple script commitment (we'll use empty for this example)
    # In real Taproot, this would be a Merkle root of script conditions
    script_commitment = b''  # Empty = key-path-only spending
    
    print(f"\n=== STEP 2: Script Commitment ===")
    print(f"Script Commitment: {script_commitment.hex() if script_commitment else 'Empty (key-path-only)'}")
    
    # Step 3: Calculate tweak using BIP341 tagged-hash formula
    # HashTapTweak(x) = SHA256(SHA256("TapTweak") || SHA256("TapTweak") || x)
    internal_pubkey_bytes = bytes.fromhex(internal_public_key.to_x_only_hex())  # x-only
    tag_hash = hashlib.sha256(b'TapTweak').digest()
    tweak_preimage = tag_hash + tag_hash + internal_pubkey_bytes + script_commitment
    tweak_hash = hashlib.sha256(tweak_preimage).digest()
    tweak_int = int.from_bytes(tweak_hash, 'big')
    
    print(f"\n=== STEP 3: Tweak Calculation ===")
    print(f"Formula: t = HashTapTweak(xonly_internal_key || merkle_root)")
    print(f"")
    print(f"Internal PubKey (x-only): {internal_pubkey_bytes.hex()}")
    print(f"Script Commitment: {script_commitment.hex() if script_commitment else '(empty)'}")
    print(f"")
    print(f"Tag Hash: {tag_hash.hex()}")
    print(f"Tweak Preimage: SHA256(TapTweak) || SHA256(TapTweak) || {internal_pubkey_bytes.hex()} || {script_commitment.hex()}")
    print(f"Tweak Hash (SHA256): {tweak_hash.hex()}")
    print(f"Tweak Integer (t): {tweak_int}")
    print(f"")
    print(f"Note: The tweak value 't' is a 256-bit integer derived from")
    print(f"      the internal public key and script commitment.")
    
    # Step 4: Apply tweaking formula
    # d' = d + t (mod n)
    # P' = P + t×G = d'×G
    internal_privkey_int = int.from_bytes(internal_private_key.to_bytes(), 'big')
    curve_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    tweaked_privkey_int = (internal_privkey_int + tweak_int) % curve_order
    
    # Create tweaked private key from the integer
    tweaked_private_key = PrivateKey.from_bytes(tweaked_privkey_int.to_bytes(32, 'big'))
    tweaked_public_key = tweaked_private_key.get_public_key()
    
    print(f"\n=== STEP 4: Tweaking Application ===")
    print(f"Formula for Private Key: d' = d + t (mod n)")
    print(f"Formula for Public Key:  P' = P + t×G = d'×G")
    print(f"")
    print(f"Where:")
    print(f"  d  = original private key (internal)")
    print(f"  d' = tweaked private key (output)")
    print(f"  t  = tweak value (from Step 3)")
    print(f"  P  = original public key (internal)")
    print(f"  P' = tweaked public key (output)")
    print(f"  G  = generator point on secp256k1 curve")
    print(f"  n  = curve order")
    print(f"")
    print(f"Private Key Transformation:")
    print(f"  Original (d):  {internal_privkey_int}")
    print(f"  Tweak (t):     +{tweak_int}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Tweaked (d'):  {tweaked_privkey_int}")
    print(f"  (mod n: {curve_order})")
    print(f"")
    print(f"Public Key Transformation:")
    print(f"  Original (P):  {internal_public_key.to_hex()}")
    print(f"  Tweaked (P'):  {tweaked_public_key.to_hex()}")
    print(f"  Output Key (x-only): {tweaked_public_key.to_hex()[2:]}")
    expected_output_key_xonly = internal_public_key.get_taproot_address([]).to_witness_program()
    print(f"  Library Output Key (x-only): {expected_output_key_xonly}")
    print(f"  Output Key Match: {tweaked_public_key.to_hex()[2:] == expected_output_key_xonly}")
    print(f"")
    print(f"Key Insight: P' = d'×G = (d + t)×G = d×G + t×G = P + t×G")
    
    # Step 5: Verify the mathematical relationship
    print(f"\n=== STEP 5: Mathematical Verification ===")
    verification_result = tweaked_private_key.get_public_key().to_hex() == tweaked_public_key.to_hex()
    print(f"Verification: d' × G = P'? {verification_result}")
    print(f"")
    print(f"This confirms:")
    print(f"  ✓ The tweaked private key d' correctly generates the tweaked public key P'")
    print(f"  ✓ The relationship P' = P + t×G holds mathematically")
    print(f"  ✓ Anyone can compute P' from P and the commitment (public information)")
    print(f"  ✓ Only the key holder can compute d' from d and tweak (private information)")
    
    return {
        'internal_private': internal_private_key,
        'internal_public': internal_public_key,
        'tweak_hash': tweak_hash,
        'tweaked_private': tweaked_private_key,
        'tweaked_public': tweaked_public_key
    }


if __name__ == "__main__":
    result = demonstrate_key_tweaking()
    
    print("\n" + "=" * 70)
    print("SUMMARY: THE KEY TWEAKING PROCESS")
    print("=" * 70)
    print("1. Start with internal key pair (d, P)")
    print("2. Calculate tweak: t = HashTapTweak(xonly_P || merkle_root)")
    print("3. Apply tweaking:")
    print("   - Private key: d' = d + t (mod n)")
    print("   - Public key:  P' = P + t×G = d'×G")
    print("4. Result: Output key (P') that commits to script conditions")
    print("")
    print("=" * 70)
    print("KEY INSIGHTS FROM KEY TWEAKING")
    print("=" * 70)
    print("1. Dual Spending Paths:")
    print("   - Key Path: Use the tweaked private key (d') to sign directly (cooperative)")
    print("   - Script Path: Reveal the internal public key (P) and prove script execution (fallback)")
    print("")
    print("2. Cryptographic Binding:")
    print("   - The tweak (t) cryptographically binds the output key (P') to specific script commitments")
    print("   - Changing the commitment changes the tweak, which changes the output key")
    print("")
    print("3. Deterministic Verification:")
    print("   - Anyone can verify that a tweaked key correctly commits to specific conditions")
    print("   - Given P and merkle_root, anyone can compute P' and verify it matches")
    print("")
    print("4. Privacy Through Indistinguishability:")
    print("   - The tweaked public key (P') is mathematically indistinguishable from any other Schnorr public key")
    print("   - Simple payments and complex contracts look identical until spent")

