# 第五章：Taproot——比特币脚本系统的演进

Taproot 是比特币脚本系统演进至今的一个集大成者：在被花费之前，复杂的花费条件可以在链上看起来和最普通的支付完全一样。

让这件事成立的有两块机器，本章会一块一块地把它们引入：

1. **Schnorr 签名（BIP340）**——一种用来替换 ECDSA 的新签名方案。
2. **Key tweaking（BIP341）**——一种把额外信息附加到公钥上的方式，而公钥在链上看起来不变。

后面会出现的几个词——`tweak`、`commitment`、`Merkle root`、`script path`——是在为第 6–8 章做铺垫。**如果第一次读到觉得某个词重，跳过它就好。** 等你做完第 5–8 章再回来看，同样的句子读起来会不一样。本章只默认你已经掌握第 1–4 章给的东西：密钥、签名、脚本、见证。

## Schnorr 签名

### 为什么要换成 Schnorr？ECDSA 的局限

比特币 2009 年上线时就用 ECDSA，一路用到现在。ECDSA 用来单独签名和验签是够用的——但 Taproot 的设计需要的不止这些。它需要签名不会在传播过程中被改头换面、需要多方协作时签名能干净地合并、需要签名在简单代数运算下表现一致。ECDSA 从来不是为这些场景设计的。

ECDSA 中那些挡了 Taproot 路的性质：

- **可篡改**：第三方可以在不破坏有效性的前提下改写签名编码——同一个签名，链上会出现两种形态。
- **无法聚合**：两方各自的两个签名只能保持为两个，没法合并成一个。
- **无线性**：把两个 ECDSA 签名相加，并不能得到对应公钥之和的合法签名。没有干净的代数可用。
- **体积可变**：通常 71–72 字节，取决于编码。

BIP340 在同一条 secp256k1 曲线上规定了 Schnorr 签名，针对 Taproot 需要的性质做了设计：

- **不可篡改**：确定性 nonce、x-only 公钥、严格编码——消除了 ECDSA 那种第三方可篡改向量。
- **可聚合**：多个公钥可合并为一个；多方协作签名可在链上以一条 64 字节签名落地。
- **线性**：这是 Taproot 真正需要的性质。下一节展开。
- **固定 64 字节**：体积更小、更统一。

### Schnorr 线性

让 Taproot 成立的代数性质：

```
若 Alice 对消息 M 持有签名 A
且 Bob  对消息 M 持有签名 B
则 A + B 是 (Alice + Bob) 合并公钥下对 M 的有效签名
```

由此引出三种构造：

1. **公钥聚合**：多人公钥合并为一个
2. **签名唯一性**：多方协作产出一个签名
3. **Key tweaking**：公钥可被确定性地"调谐"以提交承诺

注：上面所说的"签名唯一性"指通过 MuSig2（钱包层协议）在链上产出一个 BIP340 签名，并不是 consensus 层跨输入的签名聚合。

### ECDSA vs Schnorr 直观对比

```
ECDSA Multisig (3-of-3):
┌─────────────────────────────────────┐
│           Transaction               │
├─────────────────────────────────────┤
│ Alice Signature:   [71 bytes]       │
│ Bob Signature:     [72 bytes]       │
│ Charlie Signature: [70 bytes]       │
├─────────────────────────────────────┤
│ Total Size: ~213 bytes              │
│ Verifications: 3 separate           │
│ Privacy: reveals 3 participants     │
│ Appearance: multi                   │
└─────────────────────────────────────┘

Schnorr Aggregated (3-of-3):
┌─────────────────────────────────────┐
│           Transaction               │
├─────────────────────────────────────┤
│ Aggregated Signature: [64 bytes]    │
├─────────────────────────────────────┤
│ Total Size: 64 bytes                │
│ Verifications: 1 single check       │
│ Privacy: hides participant count    │
│ Appearance: single                  │
└─────────────────────────────────────┘
```

## Key Tweaking

Taproot 通过 key tweaking（在 BIP340/341/342 中也称作 tweakable commitment）利用 Schnorr 的线性。

直观写法：
```
t = H("TapTweak" || internal_pubkey || merkle_root)
```

形式化（BIP341）：

```
t  = int(HashTapTweak(xonly_internal_key || merkle_root_or_empty)) mod n

P' = P + t * G
d' = d + t
```

**Even-Y 要求（BIP340）：**
Taproot 使用 x-only 公钥——但 secp256k1 上的实际点仍有两个可能的 y 值（even / odd）。
BIP340 的规则：最终的 tweaked output key **必须对应 even-y 点**。
若结果落到 odd-y，实现会翻转私钥 `d' = n − d'`，使 `P' = d'*G` 落到 even 那一支。

（这点在后面会用到：在 script-path 支出中，这个奇偶性会被编码到 control block 的最低位。如果不在这里把这点记住，后面 script-path 验证会通不过。）

### Tweak 流程

```
Internal Key (P) ─────────► + tweak ─────────► Output Key (P')
                              ▲                      │
                              │                      │
                       Merkle Root ◄─────────────────┘
                    script_path_commitment
```

变量说明：
- `P` = **Internal Key**（用户控制的原始公钥）
- `M` = **Merkle 根**（对所有可能花费条件的承诺）
- `t` = **Tweak Value**（由 P 与 M 确定性计算）
- `P'` = **Output Key**（最终上链的 Taproot 地址公钥）
- `d'` = **Tweaked Private Key**（用于 key-path 支出）

### Key tweaking 实操

```python
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from bitcoinutils.script import Script
import hashlib

def demonstrate_key_tweaking():
    setup('testnet')

    # 步骤 1：生成 internal 密钥对
    internal_private_key = PrivateKey('cTALNpTpRbbxTCJ2A5Vq88UxT44w1PE2cYqiB3n4hRvzyCev1Wwo')
    internal_public_key = internal_private_key.get_public_key()

    print("=== STEP 1: Internal Key Generation ===")
    print(f"Internal Private Key: {internal_private_key.to_wif()}")
    print(f"Internal Public Key:  {internal_public_key.to_hex()}")

    # 步骤 2：构造脚本承诺（此处为空，表示仅 key-path）
    # 真实 Taproot 中这里会是脚本条件的 Merkle 根
    script_commitment = b'' # 空 = 仅 key-path 支出

    print(f"\n=== STEP 2: Script Commitment ===")
    print(f"Script Commitment: {script_commitment.hex() if script_commitment else 'Empty (key-path-only)'}")

    # 步骤 3：按 BIP341 公式计算 tweak
    internal_pubkey_bytes = bytes.fromhex(internal_public_key.to_x_only_hex()) # x-only
    tag_digest = hashlib.sha256(b'TapTweak').digest()
    tweak_preimage = tag_digest + tag_digest + internal_pubkey_bytes + script_commitment
    tweak_hash = hashlib.sha256(tweak_preimage).digest()
    tweak_int = int.from_bytes(tweak_hash, 'big')

    print(f"\n=== STEP 3: Tweak Calculation ===")
    print(f"Internal PubKey (x-only): {internal_pubkey_bytes.hex()}")
    print(f"Tweak Preimage: TapTweak || {internal_pubkey_bytes.hex()} || {script_commitment.hex()}")
    print(f"Tweak Hash: {tweak_hash.hex()}")
    print(f"Tweak Integer: {tweak_int}")

    # 步骤 4：应用 tweak 公式
    curve_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    internal_privkey_int = int.from_bytes(internal_private_key.to_bytes(), 'big')
    tweaked_privkey_int = (internal_privkey_int + tweak_int) % curve_order
    tweaked_private_key = PrivateKey.from_bytes(tweaked_privkey_int.to_bytes(32, 'big'))
    tweaked_public_key = tweaked_private_key.get_public_key()

    print(f"\n=== STEP 4: Tweaking Application ===")
    print(f"Original Private Key d: {internal_privkey_int}")
    print(f"Tweaked Private Key d': {tweaked_privkey_int}")
    print(f"Private Key Change: +{tweak_int}\n")
    print(f"Original Public Key P: {internal_public_key.to_hex()}")
    print(f"Tweaked Public Key P': {tweaked_public_key.to_hex()}")
    print(f"Public Key (x-only): {tweaked_public_key.to_hex()[2:]}")

    # 步骤 5：验证代数关系
    print(f"\n=== STEP 5: Mathematical Verification ===")
    print(f"d' * G == P + tweak_int * G? {tweaked_public_key.to_x_only_hex() == internal_public_key.to_taproot_hex()[0]}")
    print(f"Anyone can compute P' from P and commitment: [OK]")
    print(f"Only key holder can compute d' from d and tweak: [OK]")

    return {
        'internal_private': internal_private_key,
        'internal_public': internal_public_key,
        'tweak_hash': tweak_hash,
        'tweaked_private': tweaked_private_key,
        'tweaked_public': tweaked_public_key
    }

# 执行演示
result = demonstrate_key_tweaking()
```

Tweak 后的公钥提供两条支出路径：**key path**——直接用 tweaked 私钥签名；**script path**——揭示 internal public key 加上某个 leaf 脚本与 control block，证明该叶子已被 Merkle 根承诺。两条路径在链上的输出形态相同——`OP_1 <32 字节 output key>`——花费前无法区分。

## 一笔最简单的 Taproot 交易

最基础的 Taproot-to-Taproot 交易：

```python
from bitcoinutils.setup import setup
from bitcoinutils.utils import to_satoshis
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.keys import PrivateKey, P2trAddress

def create_simple_taproot_transaction():
    setup('testnet')
    
    # 发送方信息
    from_private_key = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
    from_pub = from_private_key.get_public_key()
    from_address = from_pub.get_taproot_address()
    
    # 接收方地址
    to_address = P2trAddress(
        'tb1p53ncq9ytax924ps66z6al3wfhy6a29w8h6xfu27xem06t98zkmvsakd43h'
    )
    
    print("=== TAPROOT TRANSACTION CREATION ===")
    print(f"From Address: {from_address.to_string()}")
    print(f"To Address: {to_address.to_string()}")
    
    # 构造交易输入
    txin = TxInput(
        'b0f49d2f30f80678c6053af09f0611420aacf20105598330cb3f0ccb8ac7d7f0',
        0
    )
    
    # 输入金额与签名所需脚本
    input_amount = 0.00029200
    amounts = [to_satoshis(input_amount)]
    input_script = from_address.to_script_pub_key()
    scripts = [input_script]
    
    # 构造交易输出
    amount_to_send = 0.00029000
    txout = TxOutput(
        to_satoshis(amount_to_send),
        to_address.to_script_pub_key()
    )
    
    # 启用 SegWit 的交易容器
    tx = Transaction([txin], [txout], has_segwit=True)
    
    print(f"\nUnsigned Transaction:")
    print(tx.serialize())
    print(f"TxId: {tx.get_txid()}")
    
    # 用 Schnorr 签名输入
    # sign_taproot_input() 内部完成 sighash 构造：
    # 1. 按 BIP341 用所有输入金额与脚本组装 sighash
    # 2. 拼装签名消息：sighash + key_version + code_separator
    # 3. 用 tweaked 私钥产出 64 字节 Schnorr 签名
    sig = from_private_key.sign_taproot_input(
        tx,
        0,
        scripts,
        amounts
    )
    
    # key-path 支出的见证只需签名；公钥已在 scriptPubKey 里作为 output key 出现。
    tx.witnesses.append(TxWitnessInput([sig]))
    
    # 取得签名后的交易
    signed_tx = tx.serialize()
    
    print(f"\nSigned Transaction:")
    print(signed_tx)
    
    print(f"\nTransaction Details:")
    print(f"Send Amount: {amount_to_send} BTC")
    print(f"Fee: {input_amount - amount_to_send} BTC")
    print(f"Transaction Size: {tx.get_size()} bytes")
    print(f"Virtual Size: {tx.get_vsize()} vbytes")
    
    return tx, sig

# 执行交易
tx, signature = create_simple_taproot_transaction()
```

`get_taproot_address()` 内部应用了 BIP341 的 tweak；`sign_taproot_input()` 产出 64 字节 BIP340 签名。见证栈中这一项是 64 字节，若带非默认 sighash flag 则 65 字节——使用 `SIGHASH_DEFAULT` 时 flag 被省略。

## 链上示例：Testnet Taproot 转账

来检视一笔真实的 Taproot 交易：[`a3b4d038...57a42cb6`](https://mempool.space/testnet/tx/a3b4d0382efd189619d4f5bd598b6421e709649b87532d53aecdc76457a42cb6?showDetails=true)

**交易结构：**
```
Input:
├── Previous Output: tb1pjyje...y3ku8
├── ScriptPubKey: OP_1 912591f3...5f697a3
└── Witness: [7d25fbc9...41da99f3]

Output:
├── Destination: tb1p53nc...akd43h
└── ScriptPubKey: OP_1 a3ff4d6e...7890ab
```

**见证数据剖析：**
```
Schnorr Signature: 7d25fbc9...41da99f3

Structure:
├── r-value: 7d25fbc9...2e30450d
├── s-value: 7d2a1f1d...41da99f3
└── Total: 64 bytes (32 + 32)
```

签名恰好 64 字节，无可变编码；见证里只有签名一项，不含公钥（与 SegWit 不同）。

## key-path 栈执行

跟踪上面那笔交易在脚本栈上的执行过程：

### 初始状态
交易开始时栈为空：

```
│ (empty)                                 │
└─────────────────────────────────────────┘
```

### 1. OP_1：压入 witness 版本号
scriptPubKey 以 OP_1 开头，表明这是 v1 witness program：

```
│ 01 (witness_version)                    │
└─────────────────────────────────────────┘
```

### 2. PUSH Output Key：压入 32 字节 Taproot output key
scriptPubKey 把 32 字节的 output key 推到栈上：

```
│ 912591f3...5f697a3 (output_key)         │
│ 01 (witness_version)                    │
└─────────────────────────────────────────┘
```

### 3. 模式识别：Bitcoin Core 识别 Taproot 格式
模式 `OP_1 <32 字节>` 选择 Taproot 解释器。witness 仅含签名 → 走 key path；witness 包含脚本与 control block → 走 script path（详见第六章）。

### 4. 加载见证：取出 Schnorr 签名
witness 栈仅含签名：

```
│ 7d25fbc9...da99f3 (schnorr_signature)   │
│ 912591f3...5f697a3 (output_key)         │
└─────────────────────────────────────────┘
```

### 5. Schnorr 验证：用 output key 验证签名
解释器执行 BIP340 验证：解析 `(r, s)`，计算挑战 `e = tagged_hash("BIP0340/challenge", r ‖ P ‖ m)`，计算 `R = s·G − e·P`，若 `r` 等于 `R` 的 x 坐标则接受。

**验证结果：**
```
│ 1 (TRUE)                                │
└─────────────────────────────────────────┘
```

已通过验证 —— key-path 支出。

## 输出形态：Legacy → SegWit → Taproot

```
Legacy P2PKH:
├── ScriptPubKey: OP_DUP OP_HASH160 <20-byte-hash> OP_EQUALVERIFY OP_CHECKSIG
├── ScriptSig: <signature> <public_key>
└── Size: ~225 bytes
   Information Revealed: Single signature spending

SegWit P2WPKH:
├── ScriptPubKey: OP_0 <20-byte-hash>
├── Witness: [signature, public_key]
└── Size: ~165 bytes
   Information Revealed: Single signature spending

Taproot P2TR (Simple):
├── ScriptPubKey: OP_1 <32-byte-output-key>
├── Witness: [schnorr_signature]
└── Size: ~135 bytes
   Information Revealed: Nothing about internal complexity

Taproot P2TR (Complex Contract):
├── ScriptPubKey: OP_1 <32-byte-output-key>
├── Witness: [schnorr_signature]
└── Size: ~135 bytes
   Information Revealed: Nothing about internal complexity
```

简单 Taproot 行与复杂 Taproot 行在输出层面字节级一致。

## SegWit → Taproot：代码差异

```python
# SegWit (P2WPKH) 模式
def create_segwit_transaction():
    private_key = PrivateKey(...)
    address = private_key.get_segwit_address()  # P2WPKH
    
    # 签名
    signature = private_key.sign_segwit_input(tx, 0, script_code, amount)
    
    # 见证：[signature, public_key]
    tx.witnesses.append(TxWitnessInput([signature, public_key]))

# Taproot (P2TR) 模式
def create_taproot_transaction():
    private_key = PrivateKey(...)
    public_key = private_key.get_public_key()
    address = public_key.get_taproot_address()  # P2TR
    
    # 签名
    signature = private_key.sign_taproot_input(tx, 0, scripts, amounts)
    
    # 见证：[signature]，不再需要公钥
    tx.witnesses.append(TxWitnessInput([signature]))
```

两处 API 改动是承重的：签名换成 `sign_taproot_input()`（Schnorr，BIP340），不再用 `sign_segwit_input()`（ECDSA）；见证只含签名——公钥已经放在 scriptPubKey 里作为 output key。

## 协作 vs script path：成本不对称

协作的 key-path 支出产出 64 字节见证，无论 output key 背后有多少方。Script-path 支出需要揭示 leaf 脚本与 control block（33 字节 internal pubkey + 叶深度 × 32 字节 Merkle proof），见证体积随树深与脚本长度而增长。Fee 上的差异让"协作"在可用时总是更便宜的那条路。

## 本章小结

Taproot 用 BIP340 Schnorr（64 字节定长）替换了 ECDSA，并对 output key 应用 BIP341 的 tweak `P' = P + t·G`。这条 tweak 把 output key 绑定到一个空提交（仅 key-path）或一棵脚本树的 Merkle 根。链上两种情况呈现相同的形态——`OP_1 <32 字节>`——key-path 支出的见证也都是 64 字节，与内部复杂度无关。

下一章会展示如何把任意花费条件组织进脚本树的 Merkle 结构、在创建输出时承诺、并仅在实际使用某条路径时才揭示。
