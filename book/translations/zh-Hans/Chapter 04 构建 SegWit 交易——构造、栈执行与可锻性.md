# 第 4 章：构建 SegWit 交易——构造、栈执行与可锻性

隔离见证（Segregated Witness，SegWit）把签名数据从交易的其余部分里分离出来。本章从头到尾构建一笔真实的 SegWit 交易——构造、签名、序列化、追踪执行——用 testnet 数据，展示这种分离如何修掉可锻性（malleability），并搭起 Taproot 后面要依赖的见证模型。

## 4.1 交易可锻性：SegWit 解决的问题

### 传统交易结构 vs SegWit

传统交易把一切哈希在一起得到 TXID。SegWit 把见证移出这个哈希：

```
Legacy Transaction Structure:
┌─────────────────────────────────────────┐
│ Version │ Inputs │ Outputs │ Locktime   │
│         │ ┌─────┐│         │            │
│         │ │ScSig││         │            │  } All included in TXID
│         │ │     ││         │            │
│         │ └─────┘│         │            │
└─────────────────────────────────────────┘
           ↓
    TXID = SHA256(SHA256(entire_transaction))


SegWit Transaction Structure:
┌─────────────────────────────────────────┐
│ Version │ Inputs │ Outputs │ Locktime   │  } Base Transaction
│         │ ┌─────┐│         │            │
│         │ │Empty││         │            │
│         │ │ScSig││         │            │
│         │ └─────┘│         │            │
└─────────────────────────────────────────┘
                                             } TXID = SHA256(SHA256(base_only))
┌─────────────────────────────────────────┐
│        Witness Data (Separated)         │  } Committed separately
│    ┌─────────────────────────────────┐  │      (For P2WPKH)
│    │ Signature │ Public Key          │  │
│    └─────────────────────────────────┘  │
└─────────────────────────────────────────┘
           ↓
    WTXID = SHA256(SHA256(entire_transaction[base + witness]))
```

正是这一处改动——见证数据移出 TXID——消除了可锻性。下一节说明旧结构当初为什么会可锻。

### 可锻性问题

在 SegWit 之前，第三方可以在不破坏签名的前提下给它重新编码，而这样做会改变交易的 TXID。ECDSA 签名用 DER（Distinguished Encoding Rules）序列化，同一个签名有不止一种合法的 DER 编码。例如：

- **原始签名**：`304402201234567890abcdef...`（71 字节）
- **可锻版本**：`3045022100001234567890abcdef...`（72 字节，补了零）

两种编码验证出来是同一个签名，但字节不同。由于传统比特币把整个 scriptSig——签名也在里面——折进 TXID，这两种编码就让同一笔经济交易有了两个不同的 TXID。

这会破坏任何把后续交易钉在前一笔 TXID 上的协议——闪电网络尤甚：

```
Lightning Channel Setup:
Funding TX (TXID_A) -> Commitment TX -> Timeout TX
                          ↓              ↓
                     References      References
                       TXID_A         TXID_B

If TXID_A changes due to malleability:
-> Commitment TX becomes invalid
-> Timeout TX becomes invalid  
-> Entire channel unusable
```

像这样的预签名交易链，假定 funding 的 TXID 是固定的。一旦它被锻改，建在它之上的每一笔交易都成了孤儿。

### Legacy 与 SegWit 代码对比

这个改动直接体现在你怎么签名上。在 legacy P2PKH 里，签名进 scriptSig：

**Legacy P2PKH Signing:**
```python
# Legacy transaction signing
sk = PrivateKey(private_key_wif)
from_addr = P2pkhAddress(from_address)

# Create locking script for P2PKH
previous_locking_script = Script([
    "OP_DUP",
    "OP_HASH160", 
    from_addr.to_hash160(),
    "OP_EQUALVERIFY",
    "OP_CHECKSIG"
])

# Sign and set unlocking script
sig = sk.sign_input(tx, 0, previous_locking_script)
pk = sk.get_public_key().to_hex()
unlocking_script = Script([sig, pk])
tx_in.script_sig = unlocking_script  # Signature goes in scriptSig
```

在 SegWit P2WPKH 里，scriptSig 留空，签名进见证。两个细节要紧：你调 `sign_segwit_input`（不是 `sign_input`），而且 SegWit 签名需要输入金额：

**SegWit P2WPKH Signing:**
```python
# SegWit transaction signing
# CRITICAL: Must use sign_segwit_input, not sign_input
# Get script_code from public key's legacy address (required for SegWit)
script_code = public_key.get_address().to_script_pub_key()

signature = private_key.sign_segwit_input(
    tx,
    0,
    script_code,  # Legacy P2PKH format script code
    to_satoshis(utxo_amount)  # Input amount required for SegWit
)

# Set empty scriptSig (required for native SegWit)
txin.script_sig = Script([])

# Set witness data using TxWitnessInput wrapper
tx.witnesses.append(TxWitnessInput([signature, public_key.to_hex()]))
```

有两点先记下、后面用：`script_code` 取自这把密钥的 *legacy* P2PKH 形式，而输入金额现在也是被签的一部分。两者都是 BIP143 的要求，等 §4.4 追踪执行时就能看到它们各自为什么出现。

## 4.2 构建一笔完整的 SegWit 交易

我们一步步构建一笔真实的 SegWit 交易，盯着每个阶段字节的变化。

### 交易准备

```python
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey, P2wpkhAddress
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.utils import to_satoshis
from bitcoinutils.script import Script

setup('testnet')

# Create keys and addresses
private_key = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
public_key = private_key.get_public_key()
from_address = public_key.get_segwit_address()
to_address = P2wpkhAddress('tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4')

print(f"From: {from_address.to_string()}")
print(f"To:   {to_address.to_string()}")
```

**Output:**
```
From: tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4
To:   tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4
```

这里 from 和 to 是同一个地址——这是一笔自转账，好让例子只用一把密钥。

**注：** 这是一笔成功广播过的真实 testnet 交易：[`271cf628...6084e3e6`](https://mempool.space/testnet/tx/271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6?showDetails=true)。

## 4.3 SegWit 交易构造与分析

### 阶段 1：创建未签名交易

```python
# UTXO information (real testnet transaction)
utxo_txid = '1454438e6f417d710333fbab118058e2972127bdd790134ab74937fa9dddbc48'
utxo_vout = 0
utxo_amount = 1000  # sats

# Create transaction components
txin = TxInput(utxo_txid, utxo_vout)
txout = TxOutput(to_satoshis(0.00000666), to_address.to_script_pub_key())

# Build unsigned transaction (has_segwit=True required for witness data)
tx = Transaction([txin], [txout], has_segwit=True)
print(f"Unsigned TX: {tx.serialize()}")
```

**Unsigned Transaction Output:**
```text
0200000000010148bcdd9dfa3749b74a1390d7bd272197e2588011abfb3303717d41
6f8e4354140000000000fdffffff019a02000000000000160014c5b28d6bba91a269
3a9b1876bcd3929323890fb200000000
```

**Parsed Components:**
```
Version:      02000000
Marker:       00 (SegWit indicator)
Flag:         01 (SegWit version)
Input Count:  01
TXID:         1454438e...9dddbc48
VOUT:         00000000
ScriptSig:    00 (empty, 0 bytes)
Sequence:     fffffffd (RBF enabled - Replace-By-Fee)
Output Count: 01
Value:        9a02000000000000 (666 sats)
Script Len:   16 (22 bytes)
ScriptPubKey: 0014c5b28d6bba91a2693a9b1876bcd3929323890fb2
Locktime:     00000000
```

哪怕还没签名，交易也已经带着 SegWit marker/flag（`00 01`）和一个空的 scriptSig。还没有见证——那是下一阶段的事。

### 阶段 2：加上 SegWit 签名

```python
# CRITICAL: Get script_code from public key's legacy address
# This must be in P2PKH format (76a914...88ac), not SegWit format
script_code = public_key.get_address().to_script_pub_key()

# Sign for SegWit using sign_segwit_input (not sign_input)
signature = private_key.sign_segwit_input(
    tx,
    0,
    script_code,  # Legacy P2PKH format script code
    to_satoshis(utxo_amount / 100000000)  # Input amount required
)

# Set empty scriptSig (required for native SegWit)
txin.script_sig = Script([])

# Set witness data using TxWitnessInput wrapper
public_key_hex = public_key.to_hex()
tx.witnesses.append(TxWitnessInput([signature, public_key_hex]))

# Check the differences
print(f"ScriptSig: '{txin.script_sig.to_hex()}'")  # Still empty
print(f"Witness Items: 2")
print(f"  [0] Signature: {signature[:20]}...{signature[-10:]}")
print(f"  [1] Public Key: {public_key_hex}")

# Complete signed transaction
signed_tx = tx.serialize()
print(f"Signed TX: {signed_tx}")
```

**Phase 2 Output:**
```
ScriptSig: ''
Witness Items: 2
  [0] Signature: 3044022015098d26918b...49e33c0301
  [1] Public Key: 02898711...74c8519
Signed TX:
0200000000010148bcdd9dfa3749b74a1390d7bd272197e2588011abfb3303717d41
6f8e4354140000000000fdffffff019a02000000000000160014c5b28d6bba91a269
3a9b1876bcd3929323890fb202473044022015098d26918b46ab36b0d1b50ee502b3
3d5c5b5257c76bd6d00ccb31452c25ae0220256e82d4df10981f25f91e5273be39fc
ed8fe164434616c94fa48f3549e33c03012102898711e6bf63f5cbe1b38c05e89d6c
391c59e9f8f695da44bf3d20ca674c851900000000
```

scriptSig 仍然是空的；一切授权这笔花费的东西，现在都在末尾追加的见证段里。

### 交易结构：签名前后

**签名前（阶段 1）：**
```
Standard Bitcoin Transaction Format (with SegWit marker/flag)
├── Version: 02000000
├── Marker: 00 (SegWit indicator)
├── Flag: 01 (SegWit version)
├── Input Count: 01
├── Input Data: 48bcdd9d...00fdffffff (ScriptSig empty)
├── Output Count: 01  
├── Output Data: 9a020000...3890fb2
└── Locktime: 00000000

Total: 84 bytes (base transaction)
```

**签名后（阶段 2）：**
```
SegWit Transaction Format
├── Version: 02000000
├── Marker: 00 (SegWit indicator)
├── Flag: 01 (SegWit version)  
├── Input Count: 01
├── Input Data: 48bcdd9d...00fdffffff (ScriptSig still empty)
├── Output Count: 01
├── Output Data: 9a020000...3890fb2
├── Witness Data: 0247304402...c8519 (NEW - authorization data)
└── Locktime: 00000000

Total: 191 bytes (added witness section: 82 bytes)
```

**注：** Sequence `0xfffffffd` 开启了 RBF（Replace-By-Fee），所以这笔交易之后能被一笔更高费率的版本替换——这也是浏览器给它打 "RBF" 标的原因。

**注：** marker/flag（`00 01`）只出现在序列化形式里，用来标明 SegWit。它们**不**参与 txid（它们参与 wtxid）。

### 原始交易逐字段拆解

```
[VERSION]       02000000
[MARKER]        00      (SegWit indicator)
[FLAG]          01      (SegWit version)
[INPUT_COUNT]   01
[TXID]          1454438e...9dddbc48
[VOUT]          00000000
[SCRIPTSIG_LEN] 00      (Empty - authorization moved to witness)
[SEQUENCE]      fffffffd
[OUTPUT_COUNT]  01
[VALUE]         9a02000000000000  (666 satoshis)
[SCRIPT_LEN]    16      (22 bytes)
[SCRIPTPUBKEY]  0014c5b28d6bba91a2693a9b1876bcd3929323890fb2
[WITNESS_ITEMS] 02      (2 items: signature + public key)
[SIG_LEN]       47      (71 bytes)
[SIGNATURE]     30440220...49e33c0301
[PK_LEN]        21      (33 bytes)
[PUBLIC_KEY]    02898711...74c8519
[LOCKTIME]      00000000
```

## 4.4 P2WPKH 栈执行

现在把这笔花费送进脚本解释器追踪一遍，用真实交易的数据。

### 几个部件

**锁定脚本（ScriptPubKey）：**
```
0014c5b28d6bba91a2693a9b1876bcd3929323890fb2
```

**拆解：**
- `00`：OP_0（见证版本 0）
- `14`：压入 20 字节
- `c5b28d6bba91a2693a9b1876bcd3929323890fb2`：公钥哈希（20 字节）

**见证栈（来自真实交易）：**
- 项 0：`30440220...49e33c0301`（签名，71 字节）
- 项 1：`02898711...74c8519`（公钥，33 字节）

### P2WPKH 怎么执行

一段 P2WPKH 锁定脚本就是 `OP_0 <20 字节哈希>`。Bitcoin Core 看到这个模式——见证版本 0、一个 20 字节的程序——并不会跑普通脚本。它识别出 P2WPKH，然后对见证项跑等价的 P2PKH 检查：

**等价脚本：** `OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG`

正是这种识别让 SegWit 保持向后兼容。一个 legacy 节点看到 `OP_0 <20 字节>`，把它读成 anyone-can-spend（OP_0 留下一个足够"真"的脚本），于是不理解也照样转发；一个 SegWit 节点识别出这个模式，执行见证规则。同样的机制，扩展到版本 1、32 字节程序（`OP_1 <32 字节>`），正是从第 5 章起 Taproot 输出被识别的方式。

### 栈执行追踪

**初始状态：**
```
│ (empty)                                 │
└─────────────────────────────────────────┘
```

**加载见证项：**
```
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

**OP_0 —— 压入见证版本：**
```
│ 00 (witness_version)                    │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

**从脚本压入公钥哈希：**
```
│ c5b28d6bba91...890fb2 (expected_hash)   │
│ 00 (witness_version)                    │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

到这里，解释器切进上面说的那套 P2PKH 等价执行，从见证里取出签名和公钥，跑 `OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG`：

**OP_DUP —— 复制公钥：**
```
│ 02898711e6bf...c8519 (public_key)       │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

**OP_HASH160 —— 哈希公钥：**
```
│ c5b28d6bba91...890fb2 (computed_hash)   │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```
Hash160 = RIPEMD160(SHA256(public_key))。在 BIP143 下，P2WPKH 被签的 scriptCode 恰好就是这个 P2PKH 模板——`OP_DUP OP_HASH160 <20 字节哈希> OP_EQUALVERIFY OP_CHECKSIG`——这就是为什么 §4.1 里 `script_code` 取自 `public_key.get_address().to_script_pub_key()`（legacy 形式 `76a914c5b2...890fb288ac`），而不是 SegWit 地址。

**从见证程序压入期望哈希：**
```
│ c5b28d6bba91...890fb2 (expected_hash)   │
│ c5b28d6bba91...890fb2 (computed_hash)   │
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```

**OP_EQUALVERIFY —— 两个哈希必须相等：**
```
│ 02898711e6bf...c8519 (public_key)       │
│ 304402201509...33c0301 (signature)      │
└─────────────────────────────────────────┘
```
computed_hash == expected_hash ✓

**OP_CHECKSIG —— 验证签名：**
```
│ 1 (TRUE)                                │
└─────────────────────────────────────────┘
```
对着交易做 ECDSA 验签 ✓

### 结果

这笔花费通过了：见证版本 0、公钥哈希等于那个 20 字节程序、签名验证通过——而且因为 TXID 排除了见证，这笔交易不再可锻。

SegWit 给一笔交易两个标识符：**txid**（base 交易的哈希，不含见证）和 **wtxid**（含见证）。矿工通过一个见证承诺——wtxid 的 Merkle 根，放在 coinbase 里——提交整个区块的见证数据。

## 4.5 从 SegWit 到 Taproot

SegWit 立下的三样东西，是 Taproot 直接接着用的。

**见证版本框架。** SegWit 按版本和程序长度定义输出，给后来的版本留了位子：
```
Version 0: P2WPKH (OP_0 <20-bytes>) and P2WSH (OP_0 <32-bytes>)
Version 1: P2TR (OP_1 <32-bytes>) - Taproot
```
Taproot 就是见证版本 1 加一个 32 字节程序——本章追踪的这个框架里的下一个槽位。

**抗可锻性。** 稳定的 TXID 才让预签名交易链可以安全地搭建——闪电通道和其他二层协议都依赖它。

**基于权重的费用。** SegWit 给见证字节的计费低于 base 字节：
```
Transaction Weight = (Base Size * 4) + Witness Size
Virtual Size = Weight ÷ 4
```
base 字节每个算 4 个权重单位；见证字节每个算 1 个。所以把授权数据移进见证会降低它的权重。你实际省多少，取决于交易里有多少是授权数据——这取决于结构，不是一个固定百分比。

对一个 2-of-3 多签来说差别很大，因为授权本身就大。在 legacy 形式里它待在 scriptSig 里，按满权重计：
```
scriptSig: OP_0 <sig1> <sig2> <redeemScript>
Total: ~300 bytes in scriptSig (counted at full weight)
```
在 SegWit P2WSH 里，同样的数据移到见证，每个字节只算四分之一：
```
scriptSig: <empty> (0 bytes)
witness: OP_0 <sig1> <sig2> <witnessScript>
Total: ~300 bytes in witness (charged at 1 wu/byte)
```
一笔交易里授权数据占比越大，见证折扣帮得越多——这就是为什么复杂脚本受益最大。Taproot 把这一点又推进了一步：靠密钥聚合，一笔多方花费可以只在链上放一个 64 字节签名，付的费接近单签交易。那是第 5 章起的事。

## 4.6 本章小结

我们把一笔 SegWit 交易从构造一路做到执行，看到了延续进 Taproot 的四样东西：

- **见证结构** —— 把签名从交易主体里分出来，正是脚本树和密钥聚合后面所依赖的那个切分。
- **抗可锻性** —— 把见证移出 TXID，稳住了交易 ID，这是预签名二层协议所要求的。
- **按模式执行** —— 解释器识别 `OP_0 <20 字节>` 并跑等价的 P2PKH 检查；Taproot 的 `OP_1 <32 字节>` 是同一个想法往上一个版本。
- **基于权重的费用** —— 给见证字节更低的计费，奖励把授权数据移出 base 交易。

P2TR 直接建在这四样之上，再加 Schnorr 签名、密钥聚合、Merkle 脚本树。

### 第 1–4 章讲了什么

本章把全书的基础部分讲完了。前四章是 Taproot 之前就存在的比特币：

- **第 1 章** —— 私钥、公钥，以及地址如何把它们编码。
- **第 2 章** —— Script 与栈：一个 P2PKH 输出如何锁定与解锁。
- **第 3 章** —— P2SH：对一段赎回脚本做承诺，在其上搭多签和时间锁。
- **第 4 章** —— SegWit：把见证移出交易主体，修掉可锻性。

Taproot 做的一切，都是这四样的变体——密钥与签名、在栈上运行的脚本、对脚本的承诺、以及见证模型。如果哪一样还不稳，值得在进入第 5 章前先补牢，因为接下来这四章会同时倚仗它们全部。

### 第 5–8 章：Taproot 本身

全书的第二部分是 Taproot 本体，同样一次一个机制地搭起来：

- **第 5 章** —— Schnorr 签名与 key tweak。
- **第 6 章** —— 单叶脚本路径。
- **第 7 章** —— 两片叶子与一个真正的 Merkle 根。
- **第 8 章** —— 四片叶子、两层树、多签与时间锁。

第 9–12 章随后转向应用——Ordinals、RGB、闪电、静默支付。

**下一章。** 第 5 章从 Schnorr 签名讲起——它的线性性让密钥聚合和 key tweak 成为可能，是 Taproot 的第一块。
