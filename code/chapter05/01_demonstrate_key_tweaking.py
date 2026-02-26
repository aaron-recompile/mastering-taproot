"""
Demonstrate Key Tweaking - The Bridge to Taproot

This script demonstrates the key tweaking process that enables Taproot:
- Internal key generation
- Script commitment (empty for key-path-only)
- Tweak calculation using BIP341 formula
- Tweaking application (Q = P + t×G, d' = d + t)
- Mathematical verification

Reference: Chapter 5, Section "Key Tweaking: The Bridge to Taproot" (lines 178-249)
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from ecc import *
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
    
    # Step 3: Calculate tweak using BIP341 formula
    # Extract x-only public key (skip the 0x02 or 0x03 prefix)
    internal_pubkey_hex = internal_public_key.to_hex()
    internal_pubkey_bytes = bytes.fromhex(internal_pubkey_hex[2:])  # x-only (skip prefix)
    
    # BIP341 HashTapTweak: SHA256("TapTweak" || xonly_internal_key || merkle_root)
    tweak_preimage = b'TapTweak' + internal_pubkey_bytes + script_commitment
    tweak_hash = hashlib.sha256(tweak_preimage).digest()
    tweak_int = int.from_bytes(tweak_hash, 'big')
    
    print(f"\n=== STEP 3: Tweak Calculation ===")
    print(f"Formula: t = HashTapTweak(xonly_internal_key || merkle_root)")
    print(f"")
    print(f"Internal PubKey (x-only): {internal_pubkey_bytes.hex()}")
    print(f"Script Commitment: {script_commitment.hex() if script_commitment else '(empty)'}")
    print(f"")
    print(f"Tweak Preimage: TapTweak || {internal_pubkey_bytes.hex()} || {script_commitment.hex()}")
    print(f"Tweak Hash (SHA256): {tweak_hash.hex()}")
    print(f"Tweak Integer (t): {tweak_int}")
    print(f"")
    print(f"Note: The tweak value 't' is a 256-bit integer derived from")
    print(f"      the internal public key and script commitment.")
    
    # Step 4: Apply tweaking formula
    # d' = d + t (mod n)
    # Q = P + t×G = d'×G
    #Generate tweak point t * G
    t_Point: Point = tweak_int * G
    #Generate internal point d * G
    ## ##First get integer version of private key
    internal_privkey_int = int.from_bytes(internal_private_key.to_bytes(), 'big')
    ## ## Then multiply that private key by G to get the public key. Essentially doing the same as what internal_private_key.get_public_key() did above
    P: Point = internal_privkey_int * G
    
    ## Evaluating whether the original point P has an even Y or an odd one.
    curve_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    
    if P.y.num % 2 == 0:
        negated_d = internal_privkey_int
    else:
        negated_d = curve_order - internal_privkey_int
        #Update the public key to be negated d * G so as to give the even Y coordinate
        P = negated_d * G
    
    #Add tweak point to the even Public key
    Q = P + t_Point

    #Now applying tweak to original secret key after making sure it gives an even Y coordinate above
    tweaked_privkey_int = (negated_d + tweak_int) % curve_order
    
    # Create tweaked private key from the integer
    tweaked_private_key = PrivateKey.from_bytes(tweaked_privkey_int.to_bytes(32, 'big'))
    tweaked_public_key = tweaked_private_key.get_public_key()
    
    print(f"\n=== STEP 4: Tweaking Application ===")
    print(f"Formula for Private Key: d' = d + t (mod n)")
    print(f"Formula for Public Key:  Q = P + t×G = d'×G")
    print(f"")
    print(f"Where:")
    print(f"  d  = original private key (internal)")
    print(f"  d' = tweaked private key (output)")
    print(f"  t  = tweak value (from Step 3)")
    print(f"  P  = original public key (internal)")
    print(f"  Q = tweaked public key (output)")
    print(f"  G  = generator point on secp256k1 curve")
    print(f"  n  = curve order")
    print(f"")
    print(f"Private Key Transformation:")
    print(f"  Original (d):  {negated_d}")
    print(f"  The original P point had an even Y coordinate... y(P) % 2 == 0 ? {P.y.num % 2 == 0}")
    print(f"  Tweak (t):     +{tweak_int}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Tweaked (d'):  {tweaked_privkey_int}")
    print(f"  (mod n: {curve_order})")
    print(f"")
    print(f"Public Key Transformation:")
    print(f"  Original (P):  {P.export_pubkey().hex()}")
    print(f"  Tweaked (Q):  {Q.export_pubkey().hex()}")
    print(f"  Output Key (x-only): {Q.export_pubkey(taproot=True).hex()}")
    print(f"  Notice how the tweaked public key is odd and not even from the prefix of 03...")
    print(f"")
    print(f"Key Insight: Q = d'×G = (d + t)×G = d×G + t×G = P + t×G")
    
    # Step 5: Verify the mathematical relationship
    print(f"\n=== STEP 5: Mathematical Verification ===")
    verification_result = tweaked_private_key.get_public_key().to_hex() == Q.export_pubkey().hex()
    print(f"Verification: d' × G = Q? {verification_result}")
    print(f"")
    print(f"This confirms:")
    print(f"  ✓ The tweaked private key d' correctly generates the same tweaked public key Q when the tweak is applied directly to the internal Public key")
    print(f"  ✓ The relationship Q = P + t×G holds mathematically")
    print(f"  ✓ Anyone can compute Q from P and the commitment (public information)")
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
    print("   - Public key:  Q = P + t×G = d'×G")
    print("4. Result: Output key (Q) that commits to script conditions")
    print("")
    print("=" * 70)
    print("KEY INSIGHTS FROM KEY TWEAKING")
    print("=" * 70)
    print("1. Dual Spending Paths:")
    print("   - Key Path: Use the tweaked private key (d') to sign directly (cooperative)")
    print("   - Script Path: Reveal the internal public key (P) and prove script execution (fallback)")
    print("")
    print("2. Cryptographic Binding:")
    print("   - The tweak (t) cryptographically binds the output key (Q) to specific script commitments")
    print("   - Changing the commitment changes the tweak, which changes the output key")
    print("")
    print("3. Deterministic Verification:")
    print("   - Anyone can verify that a tweaked key correctly commits to specific conditions")
    print("   - Given P and merkle_root, anyone can compute Q and verify it matches")
    print("")
    print("4. Privacy Through Indistinguishability:")
    print("   - The tweaked public key (Q) is mathematically indistinguishable from any other Schnorr public key")
    print("   - Simple payments and complex contracts look identical until spent")

