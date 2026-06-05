# Editorial Conventions — v1.0

Stable manuscript formatting conventions for cross-platform consistency
(GitHub, Obsidian, Leanpub, PDF). Mirrors GitHub issue #28.

Applies to `book/manuscript/Chapter 01-12`. The Chinese translation has its
own style guide: `book/translations/zh-Hans/STYLE.md`.

## 1. Transaction link formatting

- Abbreviate TXIDs symmetrically, `8+8`: e.g. `f4184fc5...831e9e16`.
- Use clickable links for TXIDs.
- Use explorer URLs with `?showDetails=true`.
- A TXID's first appearance in a chapter must be fully link-backed; later
  appearances may be abbreviated, but the style stays consistent.

## 2. Stack / ASCII display

- Fixed-width ASCII layout, fixed padding (aligned borders and columns).
- Use an internal ellipsis for long hex values (e.g. `304402...443d01`).
- Put human-readable explanations **outside** the stack box, not inside it.
- No emoji in alignment-sensitive blocks (ASCII tables / stack diagrams).
- Leave a blank line **before and after every fenced block** (` ``` `).
  Without it, Obsidian / Leanpub / PDF can mis-pair fences and the diagram
  (and everything after it) renders wrong, even where GitHub tolerates it.

## 3. Character stability

Prefer ASCII in code-like teaching output and alignment-sensitive sections.
Replace unstable symbols:

| Unstable | Use |
|----------|-----|
| `✓` | `[OK]` |
| `❌` | `[Wrong]` |
| `→` | `->` |
| `×` | `*` (multiplication) or `x` (a factor, e.g. `1.6x`) |
| `≥` `≤` | `>=` `<=` |

Keep the middle dot `·` for scalar multiplication (e.g. `t·G`) — it is stable
and reads better than `*` in elliptic-curve math.

## Non-goals

- No protocol-logic changes in formatting-only edits.
- No narrative restructuring in formatting-only edits.

## Review policy

Formatting changes should keep meaning unchanged, stay chapter-scoped and
easy to review, and follow the conventions above exactly.
