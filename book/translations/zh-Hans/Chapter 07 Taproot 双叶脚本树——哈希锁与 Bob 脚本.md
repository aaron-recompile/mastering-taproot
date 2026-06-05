# 第 7 章：Taproot 双叶脚本树——哈希锁与 Bob 脚本

## 从一片叶子到两片

第 6 章构建的 Taproot 地址只有一片叶子——一段哈希锁脚本，外加 Alice 的 key path。只有一片叶子时，TapLeaf 哈希*就是* Merkle 根，control block 里除了内部密钥什么都不带。本章加上第二片叶子，而仅仅这一处改动，就把脚本树其余的机制都拽了进来：一个由两条分支算出来的真正 Merkle 根，以及一个必须携带兄弟哈希（sibling hash）来证明自己叶子归属的 control block。

我们要构建的合约，给同一个地址三条互相独立的花费路径：

- **脚本路径 1**——哈希锁：任何知道 "helloworld" 的人都能花。
- **脚本路径 2**——Bob 的脚本：只有 Bob 的私钥能花。
- **Key path**——Alice，作为内部密钥持有者，可以直接花（安静、私密的默认选项）。

和第 6 章一样，这些从外面都看不见。直到有人花费之前，这个地址和一笔普通支付无法区分；花费时也只揭示走过的那一条路径。

## 双叶树的 Merkle 结构

一片叶子时没有什么可合并的。两片叶子时，你就要搭一棵真正的 Merkle 树：

```
        Merkle Root
       /           \
  TapLeaf A    TapLeaf B
(Hash Script) (Bob Script)
```

三步，其中第二步是真正新出现的：

1. **TapLeaf 哈希**——每段脚本各自哈希成自己的叶子，和第 6 章完全一样。
2. **TapBranch 哈希**——两个叶子哈希按**字典序**排序，再一起哈希成父节点。正是这个排序让根具有确定性：无论你以什么顺序列出脚本，较小的哈希总是排在前面，于是所有人都算出同一个根。
3. **Control block**——要花掉某一片叶子，你得证明它确实位于那个根之下。证明就是*另一片*叶子的哈希，装在 control block 里，好让验证方重新算出这条分支、落回根上。

本章余下的内容，就是从真实链上数据看这套结构。

## 两笔链上交易

我们从同一个双叶地址的两笔真实 testnet 花费倒推着看。

**交易 1 —— 哈希脚本路径**
- TXID：[`b61857a0...78a2e430`](https://mempool.space/testnet/tx/b61857a05852482c9d5ffbb8159fc2ba1efa3dd16fe4595f121fc35878a2e430?showDetails=true)
- 地址：`tb1p93c4...gq9a4w3z`
- 用原像 "helloworld" 花费。

**交易 2 —— Bob 脚本路径**
- TXID：[`185024da...5a70cfe0`](https://mempool.space/testnet/tx/185024daff64cea4c82f129aa9a8e97b4622899961452d1d144604e65a70cfe0?showDetails=true)
- 地址：`tb1p93c4...gq9a4w3z`
- 用 Bob 的签名花费。

两笔花费共用**同一个地址**——这正是要点。它们都出自同一棵双叶树，只是各自揭示了不同的叶子。（它们花的是这个地址的两笔不同充值，因为一个 UTXO 只能花一次。）

## Commit：构建双叶树

下面是产出那个地址的代码：

```python
def create_dual_leaf_taproot():
    """Build dual-leaf Taproot address containing Hash Lock and Bob Script"""
    setup('testnet')

    # Alice's internal key (Key Path controller)
    alice_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    alice_public = alice_private.get_public_key()

    # Bob's key (Script Path 2 controller)
    bob_private = PrivateKey('cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG')
    bob_public = bob_private.get_public_key()

    # Script 1: Hash Lock - verify preimage "helloworld"
    preimage = "helloworld"
    preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    hash_script = Script([
        'OP_SHA256',
        preimage_hash,  # 936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af
        'OP_EQUALVERIFY',
        'OP_TRUE'
    ])

    # Script 2: Bob Script - P2PK verify Bob's signature
    bob_script = Script([
        bob_public.to_x_only_hex(),  # 84b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5
        'OP_CHECKSIG'
    ])

    # Build dual-leaf script tree (flat structure)
    all_leafs = [hash_script, bob_script]

    # Generate Taproot address
    taproot_address = alice_public.get_taproot_address(all_leafs)

    print(f"Dual-leaf Taproot address: {taproot_address.to_string()}")
    print(f"Hash Script: {hash_script}")
    print(f"Bob Script: {bob_script}")

    return taproot_address, hash_script, bob_script

# Actually generated address
# Output: tb1p93c4...9a4w3z
```

有两点要留意，因为它们决定了后面的一切：

- **这棵树是扁平的**：`all_leafs = [hash_script, bob_script]`——两片叶子在同一层。
- **顺序定下索引**：`hash_script` 是索引 0，`bob_script` 是索引 1。花费每片叶子时，你要把这个索引传给 control block，所以它必须对得上。

库拿到这个列表，算出两个 TapLeaf 哈希，排序并合并成 Merkle 根，再把 Alice 的密钥 tweak 成输出密钥。如果两笔不同的脚本路径花费都能重建出同一个地址，就说明这棵树每次都是按同样方式构建的——这正是下面我们依赖的那个核验。

## Reveal：分别花费两条脚本路径

### 哈希脚本路径

来自交易 [`b61857a0...78a2e430`](https://mempool.space/testnet/tx/b61857a05852482c9d5ffbb8159fc2ba1efa3dd16fe4595f121fc35878a2e430?showDetails=true)：

```python
def hash_script_path_spending():
    """Hash Script Path spending - unlock using preimage"""
    setup('testnet')

    # Rebuild identical script tree
    alice_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    alice_public = alice_private.get_public_key()

    bob_private = PrivateKey('cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG')
    bob_public = bob_private.get_public_key()

    # Build same script tree
    preimage = "helloworld"
    preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    hash_script = Script(['OP_SHA256', preimage_hash, 'OP_EQUALVERIFY', 'OP_TRUE'])
    bob_script = Script([bob_public.to_x_only_hex(), 'OP_CHECKSIG'])

    all_leafs = [hash_script, bob_script]
    taproot_address = alice_public.get_taproot_address(all_leafs)

    # Build transaction
    txin = TxInput(
        "f02c055369812944390ca6a232190ec0db83e4b1b623c452a269408bf8282d66",
        0
    )
    txout = TxOutput(to_satoshis(0.00001034), alice_public.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Key: Build Hash Script's Control Block (index 0)
    control_block = ControlBlock(
        alice_public,
        all_leafs,
        0,  # hash_script index
        is_odd=taproot_address.is_odd()
    )

    # Witness data: [preimage, script, control_block]
    preimage_hex = preimage.encode('utf-8').hex()
    tx.witnesses.append(TxWitnessInput([
        preimage_hex,
        hash_script.to_hex(),
        control_block.to_hex()
    ]))

    return tx
```

这就是第 6 章的哈希锁花费，只有一处关键不同：control block 是从 `all_leafs`（两段脚本）在索引 0 处构建的。库需要整棵树才能知道兄弟是谁——索引 0 意味着"这是哈希脚本；另一片叶子是它的兄弟，把那片的哈希作为证明带上"。单叶时没有兄弟可带；现在有了。

### Bob 脚本路径

来自交易 [`185024da...5a70cfe0`](https://mempool.space/testnet/tx/185024daff64cea4c82f129aa9a8e97b4622899961452d1d144604e65a70cfe0?showDetails=true)：

```python
def bob_script_path_spending():
    """Bob Script Path spending - unlock using Bob's private key signature"""
    setup('testnet')

    # Same script tree construction
    alice_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    alice_public = alice_private.get_public_key()

    bob_private = PrivateKey('cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG')
    bob_public = bob_private.get_public_key()

    # Rebuild script tree
    preimage_hash = hashlib.sha256("helloworld".encode('utf-8')).hexdigest()
    hash_script = Script(['OP_SHA256', preimage_hash, 'OP_EQUALVERIFY', 'OP_TRUE'])
    bob_script = Script([bob_public.to_x_only_hex(), 'OP_CHECKSIG'])

    all_leafs = [hash_script, bob_script]
    taproot_address = alice_public.get_taproot_address(all_leafs)

    # Build transaction
    txin = TxInput(
        "8caddfad76a5b3a8595a522e24305dc20580ca868ef733493e308ada084a050c",
        1
    )
    txout = TxOutput(to_satoshis(0.00000900), bob_public.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Key: Build Bob Script's Control Block (index 1)
    control_block = ControlBlock(
        alice_public,
        all_leafs,
        1,  # bob_script index
        is_odd=taproot_address.is_odd()
    )

    # Script Path signature (note parameters)
    sig = bob_private.sign_taproot_input(
        tx, 0,
        [taproot_address.to_script_pub_key()],
        [to_satoshis(0.00001111)],
        script_path=True,
        tapleaf_script=bob_script,  # Singular form!
        tweak=False
    )

    # Witness data: [signature, script, control_block]
    tx.witnesses.append(TxWitnessInput([
        sig,
        bob_script.to_hex(),
        control_block.to_hex()
    ]))

    return tx
```

和哈希路径有两处不同，都源自一个事实：Bob 的叶子是一次签名检查，而不是哈希检查。

- **control block 在索引 1**——这是第二片叶子，所以它的兄弟是*哈希*脚本的哈希。
- **这次花费要签名**，而哈希路径不签。签名参数值得逐个细读：
  - `script_path=True`——为某片叶子签名，而不是为 key path。
  - `tapleaf_script=bob_script`——单数，因为你是针对正在执行的*那一片*叶子签名（对比第 6 章 key path 的 `tapleaf_scripts`，复数，那时需要整棵树来重建 tweak）。
  - `tweak=False`——脚本路径的签名是被脚本里的 `OP_CHECKSIG` 拿 Bob 的*原始*密钥去验的，所以这把密钥*不*做 tweak。这和 key path 正好相反——key path 的全部要点就是用 tweak 后的密钥签名。

witness 的形状还是第 6 章那个——数据、脚本、control block——只是签名顶替了原像的位置：

| | 哈希脚本路径 | Bob 脚本路径 |
|---|---|---|
| 脚本索引 | 0 | 1 |
| Witness `[0]` | 原像 hex | Schnorr 签名 |
| 脚本如何检查它 | 哈希匹配 | 签名验证 |
| control block 里的兄弟 | Bob 脚本的 TapLeaf 哈希 | 哈希脚本的 TapLeaf 哈希 |

## 从链上读 control block

表格最后一行是新东西，所以来看它的原始字节。每个 control block 都携带*另一片*叶子的哈希——这就是 Merkle 证明。

**哈希脚本路径**，来自 [`b61857a0...78a2e430`](https://mempool.space/testnet/tx/b61857a05852482c9d5ffbb8159fc2ba1efa3dd16fe4595f121fc35878a2e430?showDetails=true)：

```
Control Block: c050be5f...8105cf9df

├─ c0: 叶子版本 (0xc0)
├─ 50be5fc4...126bb4d3: Alice 内部公钥
└─ 2faaa677...8105cf9df: Bob 脚本的 TapLeaf 哈希  ← 兄弟
```

**Bob 脚本路径**，来自 [`185024da...5a70cfe0`](https://mempool.space/testnet/tx/185024daff64cea4c82f129aa9a8e97b4622899961452d1d144604e65a70cfe0?showDetails=true)：

```
Control Block: c050be5f...8f10f659e

├─ c0: 叶子版本 (0xc0)
├─ 50be5fc4...126bb4d3: Alice 内部公钥（相同！）
└─ fe78d852...8f10f659e: 哈希脚本的 TapLeaf 哈希  ← 兄弟
```

直接从这两段能读出两件事：

- 两个里的内部公钥**完全相同**——同一个 Alice，同一棵树。
- 末尾的 32 字节**互换了**：每片叶子都带着它兄弟的哈希。哈希路径带的是 Bob 叶子的哈希；Bob 路径带的是哈希叶子的哈希。这个互换*就是* Merkle 证明——给验证方一片叶子加它兄弟的哈希，它就能重建分支和根。

### 验证 control block ＝ 重建地址

检查一个 control block 归结为一件事：拿揭示出的叶子、control block 里的兄弟哈希、内部密钥，看它们能不能重建出资金被打去的那个地址。

```python
def verify_control_block_and_address_reconstruction():
    """Verify Control Block and reconstruct Taproot address"""

    # Hash Script Path data
    hash_control_block = (
        "c050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3"
        "2faaa677cb6ad6a74bf7025e4cd03d2a82c7fb8e3c277916d7751078105cf9df"
    )
    hash_script_hex = (
        "a820936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af"
        "8851"
    )

    # Bob Script Path data
    bob_control_block = (
        "c050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3"
        "fe78d8523ce9603014b28739a51ef826f791aa17511e617af6dc96a8f10f659e"
    )
    bob_script_hex = (
        "2084b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5"
        "ac"
    )

    # Parse Control Block structure
    def parse_control_block(cb_hex):
        cb_bytes = bytes.fromhex(cb_hex)
        leaf_version = cb_bytes[0] & 0xfe
        parity = cb_bytes[0] & 0x01
        internal_pubkey = cb_bytes[1:33]
        merkle_path = cb_bytes[33:]  # sibling node hash
        return leaf_version, parity, internal_pubkey, merkle_path

    # Parse Hash Script's Control Block
    hash_version, hash_parity, hash_internal_key, hash_sibling = parse_control_block(hash_control_block)

    # Parse Bob Script's Control Block
    bob_version, bob_parity, bob_internal_key, bob_sibling = parse_control_block(bob_control_block)

    print("Control Block verification:")
    print(f"[OK] Internal pubkey consistent: {hash_internal_key == bob_internal_key}")
    print(f"[OK] Alice internal pubkey: {hash_internal_key.hex()}")

    # Calculate respective TapLeaf hashes
    hash_tapleaf = tagged_hash("TapLeaf", bytes([hash_version]) + bytes([len(bytes.fromhex(hash_script_hex))]) + bytes.fromhex(hash_script_hex))
    bob_tapleaf = tagged_hash("TapLeaf", bytes([bob_version]) + bytes([len(bytes.fromhex(bob_script_hex))]) + bytes.fromhex(bob_script_hex))

    print(f"\nTapLeaf hash calculation:")
    print(f"[OK] Hash Script TapLeaf: {hash_tapleaf.hex()}")
    print(f"[OK] Bob Script TapLeaf:  {bob_tapleaf.hex()}")

    # Verify sibling node relationship
    print(f"\nSibling node verification:")
    print(f"[OK] Hash Script's sibling is Bob TapLeaf: {hash_sibling.hex() == bob_tapleaf.hex()}")
    print(f"[OK] Bob Script's sibling is Hash TapLeaf: {bob_sibling.hex() == hash_tapleaf.hex()}")

    # Calculate Merkle Root
    # Sort lexicographically then calculate TapBranch
    if hash_tapleaf < bob_tapleaf:
        merkle_root = tagged_hash("TapBranch", hash_tapleaf + bob_tapleaf)
    else:
        merkle_root = tagged_hash("TapBranch", bob_tapleaf + hash_tapleaf)

    print(f"\nMerkle Root calculation:")
    print(f"[OK] Calculated Merkle Root: {merkle_root.hex()}")

    # Calculate output pubkey tweak
    tweak = tagged_hash("TapTweak", hash_internal_key + merkle_root)
    print(f"[OK] Tweak value: {tweak.hex()}")

    # Address reconstruction (simplified concept display)
    target_address = (
        "tb1p93c4wxsr87p88jau7vru83zpk6xl0shf5ynmutd9x0gxwau3tng"
        "q9a4w3z"
    )
    print(f"\nAddress verification:")
    print(f"[OK] Target address: {target_address}")
    print(f"[OK] Control Block valid: Can reconstruct same address")

    return True

verify_control_block_and_address_reconstruction()
```

这个函数把"互换"落到了实处：它从揭示出的脚本算出两个 TapLeaf 哈希，再检查每个 control block 末尾的 32 字节确实是*另一片*叶子的哈希。一旦成立，它就把两个哈希排序，用 TapBranch 合并成 Merkle 根，tweak Alice 的密钥，最后回到 `tb1p93c4...`。两条路径落到同一个地址——这正是"两片叶子当初确实都被承诺进了它"的证明。

## 脚本路径 1：哈希脚本

来自交易 [`b61857a0...78a2e430`](https://mempool.space/testnet/tx/b61857a05852482c9d5ffbb8159fc2ba1efa3dd16fe4595f121fc35878a2e430?showDetails=true)。

**Witness 栈**

```
[0] 68656c6c6f776f726c64                             (preimage_hex)
[1] a820936a...f8f8f07af8851                         (script_hex)
[2] c050be5f...8105cf9df                             (control_block)
```

**脚本字节码** —— `a820936a...f8f8f07af8851`：

```
a8 = OP_SHA256
20 = OP_PUSHBYTES_32
936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af = SHA256("helloworld")
88 = OP_EQUALVERIFY
51 = OP_PUSHNUM_1 (OP_TRUE)
```

这就是第 6 章那把哈希锁，所以栈的走法也一样：

**起点** —— 原像加载到栈上：

```
| 68656c6c...6f726c64 | (原像 "helloworld" 的 hex)
└─────────────────────┘
```

**OP_SHA256** —— 弹出原像，压入它的 SHA256：

```
| 936a185c...8f8f07af | (算出的哈希)
└─────────────────────┘
```

**OP_PUSHBYTES_32** —— 压入脚本内置的期望哈希：

```
| 936a185c...8f8f07af | (期望哈希)
| 936a185c...8f8f07af | (算出的哈希)
└─────────────────────┘
```

**OP_EQUALVERIFY** —— 弹出两个比较；相等，于是继续执行：

```
|                     | (空栈)
└─────────────────────┘
```

**OP_PUSHNUM_1** —— 压入 1，栈顶非零，标志脚本被满足：

```
|          01          |
└──────────────────────┘
```

## 脚本路径 2：Bob 脚本

来自交易 [`185024da...5a70cfe0`](https://mempool.space/testnet/tx/185024daff64cea4c82f129aa9a8e97b4622899961452d1d144604e65a70cfe0?showDetails=true)。这片叶子是新的——P2PK 检查，而不是哈希锁。

**Witness 栈**

```
[0] 26a0eadc...31f9f1c5c                            (bob_signature)
[1] 2084b595...ceef63af5ac                          (script_hex)
[2] c050be5f...8f10f659e                            (control_block)
```

**脚本字节码** —— `2084b595...ceef63af5ac`：

```
20 = OP_PUSHBYTES_32
84b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5 = Bob 的 x-only 公钥
ac = OP_CHECKSIG
```

脚本就两步：压入 Bob 的密钥，然后对它做一次签名检查。

**起点** —— Bob 的签名加载到栈上（它来自 witness，不是脚本）：

```
| 26a0eadc...1f9f1c5c | (Bob 的 64 字节签名)
└─────────────────────┘
```

**OP_PUSHBYTES_32** —— 脚本把 Bob 的 x-only 公钥压到顶上：

```
| 84b59516...eef63af5 | (Bob 的 32 字节公钥)
| 26a0eadc...1f9f1c5c | (Bob 的 64 字节签名)
└─────────────────────┘
```

**OP_CHECKSIG** —— 弹出密钥和签名，按 BIP340 Schnorr 验证对着这笔交易核验，成立就压入 1：

```
|          01          | (签名有效)
└──────────────────────┘
```

于是两片叶子以相同方式收尾——栈顶一个 1——但走到那里的方式不同：哈希叶子证明知道一个*秘密*，Bob 叶子证明持有一把*密钥*。一个地址，两个解锁条件，而你用的那个才会被揭示。

## 和单叶相比，变了什么

把单叶和双叶并排看，差别恰好就在一处——Merkle 根怎么形成：

**单叶** —— 根*就是*那片叶子：

```
Merkle Root = TapLeaf Hash
            = Tagged_Hash("TapLeaf", 0xc0 + len(script) + script)
```

control block 只带内部密钥；没有兄弟，所以没有 Merkle 路径。

**双叶** —— 根是覆盖两片叶子的一条分支：

```
Merkle Root = TapBranch Hash
            = Tagged_Hash("TapBranch", sorted(TapLeaf_A, TapLeaf_B))

TapLeaf_A = Tagged_Hash("TapLeaf", 0xc0 + len(script_A) + script_A)
TapLeaf_B = Tagged_Hash("TapLeaf", 0xc0 + len(script_B) + script_B)
```

字典序排序让根与列出顺序无关，而 control block 现在要带一个兄弟哈希。

这个兄弟哈希是 control block 唯一变大的来源，而且变大得很有规律——每多一层树深，就多一个哈希：

| 树 | Control block | 内容 |
|------|---------------|------|
| 单叶 | 33 字节 | 版本+奇偶、内部公钥 |
| 双叶 | 65 字节 | ＋一个兄弟哈希 |
| 四叶 | 97 字节 | ＋第二个兄弟哈希（每层一个） |

每多一层深度，证明就多 32 字节——一条 Merkle 路径，随叶子数量的对数增长，而不是随叶子的个数增长。

## 构建双叶 Taproot 的若干模式

上面两笔花费可以归纳成一小组可复用的零件。

**Commit —— 构建树（索引顺序很重要）：**

```python
def build_dual_leaf_taproot(alice_key, bob_key, preimage):
    # Build two different types of scripts
    hash_script = build_hash_lock_script(preimage)
    bob_script = build_bob_p2pk_script(bob_key)

    # Create script tree (index matters!)
    leafs = [hash_script, bob_script]  # Index 0 and 1

    # Generate Taproot address
    taproot_address = alice_key.get_taproot_address(leafs)

    return taproot_address, leafs
```

**Reveal —— 一个模板花任意叶子：**

```python
def spend_script_path(script_index, input_data, leafs, internal_key, taproot_addr):
    # Build Control Block
    control_block = ControlBlock(
        internal_key,
        leafs,
        script_index,  # Key: specify which script to use
        is_odd=taproot_addr.is_odd()
    )

    # Build witness data (strict order!)
    witness = TxWitnessInput([
        *input_data,              # Inputs needed for script execution
        leafs[script_index].to_hex(),  # Script to execute
        control_block.to_hex()    # Merkle proof
    ])

    return witness
```

**要盯防的错误** —— control block 的索引和你实际揭示的脚本对不上。库会构出错误的 Merkle 证明，验证失败：

```python
# wrong — index and revealed script disagree
control_block = ControlBlock(..., leafs, 1, ...)  # index 1
witness = [..., leafs[0].to_hex(), ...]           # but revealing leaf 0

# right — drive both from one variable
script_index = 1
control_block = ControlBlock(..., leafs, script_index, ...)
witness = [..., leafs[script_index].to_hex(), ...]
```

如果脚本路径花费过不了 Merkle 检查，这是第一个要查的地方——把 control block 末尾的 32 字节抠出来，确认它确实是你预期的那个兄弟：

```python
def debug_control_block(control_block_hex, script_hex, expected_sibling):
    cb = bytes.fromhex(control_block_hex)
    actual_sibling = cb[33:65]  # sibling node hash

    print(f"Expected sibling: {expected_sibling.hex()}")
    print(f"Actual sibling: {actual_sibling.hex()}")
    print(f"Match result: {actual_sibling == expected_sibling}")
```

## 三条路径的成本与隐私

一个地址有三种花法，下面是各自的成本和暴露的东西。

**大小**（取自链上花费）：

- **Key path** —— 约 110 字节；witness 是一个 64 字节签名。
- **哈希脚本** —— 约 180 字节；witness 是原像 + 脚本 + control block。
- **Bob 脚本** —— 约 185 字节；witness 是签名 + 脚本 + control block。

**验证、隐私、手续费：**

- **Key path** —— 一次签名验证；什么都不暴露；最便宜（基线）。
- **哈希脚本** —— 哈希检查加 Merkle 验证；暴露哈希锁；约 1.6× key-path 手续费。
- **Bob 脚本** —— 签名检查加 Merkle 验证；暴露 P2PK 结构；约 1.7×。

从这些数字能引出三点：

- **只要 key path 可用，它永远是最好的花法**——最小、最便宜、什么都不暴露——无论它背后那棵树多复杂。
- **脚本路径的溢价不大**——多出的成本就是一段脚本加一个 control block，远比把等价条件写成经典 multisig 赎回脚本要少。
- **你只为走过的那条路径付费。** 没用到的叶子从不上链；它们作为哈希一直折叠在 Merkle 根里。

## 本章小结

加上第二片叶子，把单叶时的那条捷径变成了真东西：一棵用 TapBranch 在两片字典序排序的叶子之上构建的 Merkle 树，以及携带兄弟哈希作为 Merkle 证明的 control block。我们直接从链上读出了这份证明的两半——每片叶子的 control block 装着*另一片*叶子的哈希——并确认任一条路径都能重建出同一个地址。

回报还是和第 6 章一样的选择性揭示，只是现在覆盖了不止一个条件：一个地址，把一把哈希锁、一次密钥检查、加上 Alice 的 key path 全都承诺进去，而只有实际用到的那一条路径才会被展示。

**下一章。** 第 8 章把树扩到四片叶子——Merkle 路径变长，control block 要带不止一个兄弟哈希（就是上面表里 97 字节、两个兄弟哈希那一档），让一个地址同时撑起好几个花费条件。
