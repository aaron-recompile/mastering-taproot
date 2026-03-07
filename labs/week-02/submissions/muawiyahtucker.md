# Submission — Your Name

Replace "Your Name" with your name or handle.
Muaawiyah Tucker
CryptoHashReview
https://github.com/muaawiyahtucker
---

## 1. Schnorr Tradeoffs

*What are the long-term tradeoffs of Schnorr?*

Using schnorr, we gain the following properties:
1) The ability to commit to different spending conditions without having to reveal that when spending one of those conditions.
2) The ability to create more efficient multi-signature schemes that require less data to verify signatures.
3) The ability to agrigate signatures, and therefore maintaining privacy
4) The ability to remove some of the signature maluabliity issues that were associated with ECDSA
5) Fix length signatures which also gave us smaller signatures than ECDSA
6) The ability to agrigate multiple signatures for verification rather than having to verify multiple signatures in a transaction separately.

---

## 2. Key Tweaking as Commitment

*Why is key tweaking a commitment, not encryption?*

Tweaking the public key with a commityment requires the reconstruction of that data every time one needs to either receive funds or spend them. Because it is a 'reconstruction', that means its not 'encryption'. Encryption implies the ability to decrypt without knowledge of the one encrypting it given the right decryption info, but in this case, the purpose of key tweaking is to set agreed terms and parameters for which the UTXP can be spent. By constructing the output public key, one commits to those terms.

---

## 3. Key-Path vs Script-Path

*What fundamentally changes between key-path and script-path spending?*

With a Key-Path spend, all that is required is to provide a signature. It reveals nothing about any of the commitments, if they even exist or not. With a script-path, you can commit to various different types of spending conditions. Each commitement is issolated from others, and spending a particular coin on a particular leaf doesn't reveal any details about the other.
Another key difference is that with a script-path spend, you need to be able to reconstruct the merkle root before it can be spent, whereas with key-path, you don't need knowledge of what went into making that merkle root, you just need to know that merkle root.
Another fundamental change is the use of a control block in order to spend script-path scripts and not for key-path spends.
---

## 4. Merkle Sibling Ordering

*What happens if Merkle sibling order changes?*

Changing the order of the scripts doesn't necesarily change the resulting merkle root and therefore address because they are sorted when concatinated. Not even if you rearrange the order of branches in the tree as they are also sorted. However, changing the structure of the tree or swapping scripts across branches can change the merkle root and therefore address. But this is mainly meant to resolve a practical consideration as it relates to lightning channels. Organanising 2-of-2 multisigs via lightning is easier to construct without necesiating multiple rounds of communication between parties.
---

## 5. Script-Path Disclosure

*What does a script-path spend inevitably reveal?*

The script path reveals:
1) its own location in the tree,
2) the script that the leaf is made from,
3) Minimum key script depth (on the assumption that there aren't any further scripts further down the tree)
4) The internal key
5) The upper bound on script count
6) A partial description of the tree topology
