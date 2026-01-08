# Mastering Taproot (Public Draft)

### About the Book

*Mastering Taproot* is a developer-focused, reproducible guide to Bitcoin’s most powerful upgrade — Taproot.

This manuscript emphasizes:

- full code samples
- real testnet transactions
- precise stack execution
- minimal abstractions

The goal is not to “explain concepts”, but to **engineer them** — from single-leaf script spends, to multi-path Merkle tree constructions, to privacy-preserving control blocks.

Foundational Bitcoin engineering knowledge should be reproducible, inspectable, and forkable — therefore this work is published open-access.

---

### Audience

This project is intended for:

- Bitcoin protocol engineers
- Script / Taproot developers
- Wallet and key management system designers
- Researchers studying Script, Merkle commitments, or Taproot privacy
- Contributors preparing for Bitcoin Core or protocol-level work

Beginners may also use it as a structured, hands-on learning path.

---

### Status

This is an active public draft.

Updates are pushed regularly as chapters and code samples reach reproducible stability.

⸻

### Educational Use

Parts of this repository will also be used in future Bitcoin developer onboarding sessions, further supporting newcomers entering Script, Taproot, and protocol-level engineering.

**Notebook Edition (Early Preview):**

An early MyST-based notebook version is being developed alongside this repository, enabling interactive execution of the core chapters (real testnet flows) as the project continues to mature.

---

### Repository Structure

All manuscript chapters are in:  
[`book/manuscript/`](./book/manuscript/)

The table of contents is maintained at:  
[`book/manuscript/SUMMARY.md`](./book/manuscript/SUMMARY.md)

---

### How to Use This Repository

1. **Read the Manuscript**

   All chapters:
   
   [`book/manuscript/`](./book/manuscript/)
   
   Start with `SUMMARY.md` for the full outline.

2. **Run the Code**

   Every chapter's runnable examples live in [`code/`](./code/).
   
   All scripts include:
   
   - deterministic key generation
   - raw transaction hex construction
   - witness stack building
   - sighash verification
   - control block validation (Taproot)
   
   Scripts target Bitcoin testnet and require only Python 3.

3. **Verify Against the Network**

   Most examples produce:
   
   - a real testnet transaction ID
   - a decodeable raw transaction
   - validation steps you can run in Core (`decoderawtransaction`, `testmempoolaccept`, etc.)

---

### How to Contribute

Pull requests are welcome.

Typical contribution areas:

- typo fixes / formatting
- improved explanations / diagrams
- corrections to code samples
- additional reproducible testnet transactions

If you open an Issue, please include:

- chapter + section
- reproduction steps (if code)
- expected vs actual behavior

This project values *precision and reproducibility* above abstraction or opinions.

---

## 🔄 Recent Public Updates

*(latest development activity)*

Jan 6–8, 2026 — Added code examples for Chapters 6–7, covering:

• Single-leaf Taproot script tree construction

• Commit-Reveal pattern implementation

• Key Path and Script Path spending

• Dual-leaf Taproot script tree construction

• Control block verification and witness ordering

• Complete implementation with testnet-verified transactions

Chapter 6 includes four scripts demonstrating the fundamental Taproot contract pattern:

• 01_create_taproot_commitment.py

• 02_key_path_spending.py

• 03_script_path_spending.py

• 04_verify_script_execution.py

Chapter 7 includes four scripts demonstrating the full dual-path spending flow:

• 01_create_dual_leaf_taproot.py

• 02_hash_script_path_spending.py

• 03_bob_script_path_spending.py

• 04_verify_control_block.py

---

Dec 5–20, 2025 — Added code examples for Chapters 1–5, covering:

• Key generation and address encoding  

• P2PKH / P2WPKH signing  

• Complete P2SH spend flows  

• SegWit transaction construction, witness execution, and byte-level parsing  

• Taproot key tweaking (BIP340/341 math)

Chapter 4 scripts were refactored into a clear three-part structure:

• 01_legacy_vs_segwit_comparison.py  

• 02_create_segwit_transaction.py  

• 03_parse_segwit_transaction.py  

---

Recent manuscript additions:

• Chapter 9 — Ordinals & BRC-20 (Draft)  

  – Taproot witness as a general-purpose data layer  

  – Non-executable Tapscript envelopes  

  – Commit / reveal patterns with testnet examples  

---

Ongoing work (Jan 2026):

• Chapter 8 (code in progress)  

  – Full four-leaf MAST constructions  

  – Control block generation and witness ordering  

  – Testnet-verified multi-path spending examples  

---

Upcoming (as chapters reach reproducible stability):

• Chapter 10 — RGB  

  – Tapret commitments  

  – Consignment and PSBT-based workflows  

  – Regtest-reproducible examples  

  – Single-use seals and client-side validation  

• Frontier Notes & Advanced Topics  

  – Lightning with Taproot (MuSig2, PTLC, v3 anchor channels)  

  – BitVM / Citrea and Taproot-anchored computation  

  – Design-space notes connecting Ordinals → RGB → LN → BitVM into a unified Taproot framework

---

### License

- Text: **CC-BY-SA 4.0**
- Code: **MIT**

This repository is developed in the open to support reproducible Bitcoin Script engineering education.