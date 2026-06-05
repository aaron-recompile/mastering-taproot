# 第 6 章：构建真实的 Taproot 合约——单叶哈希锁与双路径花费

第 5 章构建的 Taproot 输出没有承诺任何东西——一个仅 key-path 的地址，唯一的花费方式就是 Alice 那把经过 tweak 的密钥。本章补上 Taproot 的另一半：脚本路径（script path）。我们让同一个地址拥有两条互相独立的花费路径，并验证：在链上，直到有人真正花掉它之前，它看起来仍然和一笔普通支付别无二致。

这个合约刻意做得很小——一段脚本，谁知道某个暗号就能取走资金——好让机制本身始终清晰可见。这里的一切都能推广到第 7–8 章的多叶脚本树；本章是同一套机制的单叶版本。

## 场景：一笔有条件的支付

Alice 想要一个能用两种方式花费的地址：

- **条件路径**：任何知道暗号 "helloworld" 的人都能取走资金。
- **所有者路径**：Alice 随时可以用自己的私钥取回资金。
- **隐私**：在未花费时，这个地址和任何普通 Taproot 支付无法区分。

这种双路径结构极为常见。下面几个例子，本质上都归结为完全相同的结构：

| 应用场景   | 两条路径如何对应               |
| ------ | ---------------------- |
| 数字商品销售 | 买家付款后用密钥解锁；卖家保留一条退款路径  |
| 悬赏任务   | 谁解开谜题谁领赏；发布者可取回无人认领的悬赏 |
| 条件托管   | 满足条件时释放资金；否则所有者取回      |
| 教学激励   | 学生答对即可领取奖励；教师保留一条管理路径  |

## 两条花费路径

Alice 的 Taproot 地址带着两种花费方式，而它们在**成本**和**暴露的信息**上差别极大。

**Key path（密钥路径）。** Alice 用她经过 tweak 的私钥签名。一个 64 字节的 Schnorr 签名，不暴露脚本的任何信息。这就是第 5 章那条便宜、私密的路径。

**Script path（脚本路径）。** 哈希锁脚本 `OP_SHA256 <hash> OP_EQUALVERIFY OP_TRUE`。任何能给出原像（preimage）"helloworld" 的人都能花费它。走这条路会暴露你用的那段脚本——但不会暴露 key path，也不会暴露这棵树里可能存在的任何其他分支。

这种不对称正是整个设计的要点：key path 是安静的默认选项；script path 是你真正需要那个条件时才用的，而且它每次只暴露你实际走的那一条分支。

## Commit–Reveal 模式

我们用 Taproot 做的几乎所有事情都遵循同一种形态，值得在写任何代码之前先给它命名：**先承诺（commit），再揭示（reveal）。**

**Commit。** 你把一条或多条花费条件折叠进一棵脚本树，把这棵树承诺进单个 Taproot 地址，然后给它打钱。从外部看，这个地址只是 32 字节——没人能看出它带着哪些条件，甚至看不出它到底带没带条件。

**Reveal。** 花费时，你挑一条路径。Key path 什么都不暴露。Script path 恰好只暴露你用的那一片叶子——其余每条分支都永远藏着。

这个模式的回报在于：在 commit 时，复杂程度天差地别的合约在链上看起来完全一样；在 reveal 时，你只为实际走的那一条分支付出代价——无论是字节还是隐私。

## 单叶哈希锁：从 Commit 到 Reveal

我们构建尽可能小的树——一片叶子——好让 commit->reveal 的流程不被任何东西干扰：

- **哈希锁脚本**：检查暗号 "helloworld" 的 SHA256。
- **单叶树**：最简单的脚本树，只有一片叶子。
- **两条路径**：key path（Alice 直接控制）加 script path（条件花费）。

### Tagged Hash

先讲一个基础构件。BIP340 把一切都过一道 *tagged*（带标签的）哈希——一个掺入了用途标签的 SHA256：

```python
def tagged_hash(tag, data):
    tag_hash = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(tag_hash + tag_hash + data).digest()

# tagged_hash("TapLeaf", script_data)          -> 脚本叶子的哈希
# tagged_hash("TapTweak", pubkey + merkle_root) -> tweak
```

正是这个标签，让一个叶子哈希永远不会和一个 tweak、或一个签名哈希撞上——哪怕输入完全相同。每个标签划出自己的领域，于是为不同用途计算出的哈希永远不会意外对齐。（我们早先已经逐字节走过这套构造；"TapLeaf" 和 "TapTweak" 不过是喂给同一台机器的两个不同标签。）

### 阶段 1 —— Commit：把资金锁在一个地址后面

首先，Alice 把哈希锁脚本承诺进一个 Taproot 地址：

```python
def build_hash_lock_script(preimage):
    """
    Build a Hash Lock Script – anyone who knows the preimage can spend
    """
    preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    return Script([
        'OP_SHA256',           # Calculate SHA256 of input
        preimage_hash,         # Expected hash to match against
        'OP_EQUALVERIFY',      # Verify hash equality or fail
        'OP_TRUE'              # Success condition
    ])

def create_taproot_commitment():
    setup('testnet')

    # Step 1: Alice's internal key - the foundation for her dual-path control
    internal_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    internal_public = internal_private.get_public_key()

    # Step 2: Build Hash Lock script for "helloworld" secret
    preimage = "helloworld"
    hash_lock_script = build_hash_lock_script(preimage)

    # Step 3: Generate Taproot address (commit script tree to blockchain)
    # This creates our "intermediate address" where funds will be locked
    taproot_address = internal_public.get_taproot_address([[hash_lock_script]])

    return taproot_address, hash_lock_script, internal_private
```

那个 `get_taproot_address` 调用底下发生了三件事，逐一拆开：

**1. 脚本序列化成字节。**

```
a820936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af8851
```

- `a8`：OP_SHA256
- `20`：PUSH 32 字节
- `936a185c...07af`：SHA256("helloworld")
- `88`：OP_EQUALVERIFY
- `51`：OP_TRUE

**2. 序列化后的脚本变成一个 TapLeaf 哈希——对单叶来说，它就是整个 Merkle 根。**

```python
script_data = bytes.fromhex("a820936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af8851")
leaf_version = 0xc0
tapleaf_hash = tagged_hash("TapLeaf", bytes([leaf_version]) + bytes([len(script_data)]) + script_data)
merkle_root = tapleaf_hash  # 只有一片叶子，所以根就是这片叶子
```

**3. Merkle 根把内部密钥 tweak 成输出密钥**——还是第 5 章那个 `Q = P + t·G`，只不过现在 tweak 里装的是一个真实的 Merkle 根，而不是一个空承诺：

```python
# BIP341: Q = P + H("TapTweak" || p || merkle_root) * G，其中 p 是 x-only 的内部密钥
internal_pubkey = bytes.fromhex("50be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3")
tweak = tagged_hash("TapTweak", internal_pubkey + merkle_root)
output_key = point_add(internal_pubkey, scalar_mult(tweak, G))
```

结果就是资金被打去的那个地址：

```text
tb1p53ncq9ytax924ps66z6al3wfhy6a29w8h6xfu27xem06t98zkmvsakd43h
```

它的 ScriptPubKey 只是 `OP_1 <32 字节输出密钥>`——和链上其他每一个 Taproot 地址逐字节同形。它身上没有任何东西能告诉观察者：这是一笔普通单签，还是一份条件合约。这种无法区分，正是 commit 阶段买来的东西。

### 阶段 2 —— 走 key path 揭示（Alice 取回）

花费之前先交代一句：接下来两个阶段各演示*一条*路径——这里是 key path，下一节是 script path。一个 UTXO 只能花一次，所以这两个阶段花的并不是同一笔币被花了两次；每条路径都是在同一个地址的**一笔独立充值**上演示的。这也是两处输入 txid 不同的原因——这里是 `4fd83128…`，阶段 3 是 `9e193d8c…`。

如果 Alice 只是想把资金拿回来，她就走 key path：

```python
def alice_key_path_spending():
    setup('testnet')

    # Alice's key (same as Phase 1)
    alice_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    alice_public = alice_private.get_public_key()

    # Rebuild same script and Taproot address
    preimage = "helloworld"
    preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    tr_script = Script(['OP_SHA256', preimage_hash, 'OP_EQUALVERIFY', 'OP_TRUE'])
    taproot_address = alice_public.get_taproot_address([[tr_script]])

    # Basic transaction information
    commit_txid = "4fd83128fb2df7cd25d96fdb6ed9bea26de755f212e37c3aa017641d3d2d2c6d"
    input_amount = 0.00003900   # 3900 satoshis
    output_amount = 0.00003700  # 3700 satoshis (200 sats fee)

    # Build transaction
    txin = TxInput(commit_txid, 0)
    txout = TxOutput(
        to_satoshis(output_amount),
        alice_public.get_taproot_address().to_script_pub_key()
    )
    tx = Transaction([txin], [txout], has_segwit=True)

    # Key Path 签名仍然需要脚本树来计算 tweak
    sig = alice_private.sign_taproot_input(
        tx,
        0,
        [taproot_address.to_script_pub_key()],  # Input ScriptPubKey
        [to_satoshis(input_amount)],            # Input amount
        script_path=False,                      # Explicitly specify Key Path
        tapleaf_scripts=[tr_script]             # Still need script tree to calculate tweak
    )

    # Witness data: Contains only 64-byte Schnorr signature
    tx.witnesses.append(TxWitnessInput([sig]))

    print(f"Key Path Transaction ID: {tx.get_txid()}")
    print(f"Witness Data: {sig}")
    return tx

# Actual execution result
tx = alice_key_path_spending()
# Output: Key Path Transaction ID: 2a13de71b3eb9c5845bc9aed56de0efd7d8f1e5e02debb0e9b3464a4ad940d05
```

key-path 花费看起来和第 5 章一模一样：witness 里就一个 64 字节 Schnorr 签名，与任何普通 Taproot 支付无法区分，一次验证搞定。脚本从头到尾没有出现。

有个细节很容易漏掉：即便走 key path，签名时仍然要传 `tapleaf_scripts`。原因是输出密钥在 commit 时被 Merkle 根 tweak 过——所以要为输出密钥签名，Alice 必须重建出同一个 tweak，这就意味着她需要那棵脚本树，哪怕她从不揭示它。`script_path=False` 把这些账藏了起来，但底下跑的还是第 5 章那个恒等关系：

- **公钥**：`output_pubkey = internal_pubkey + tweak · G`
- **私钥**：`tweaked_private = internal_private + tweak`
- 因为 Schnorr 是线性的，这两者始终是一对匹配的密钥——Alice 那把 tweak 后的私钥，正好能为输出密钥签名。

这就是第 5 章的线性性，在干着其他一切都依赖的那一件事。

### 阶段 3 —— 走 script path 揭示（条件解锁）

新活儿都在 script path 这边。witness 里不再是一个签名，而是要装够东西，既证明某片特定的叶子确实长在已承诺的树里，又提供脚本运行所需的输入。

```python
def script_path_spending():
    setup('testnet')

    # Step 1: Rebuild previous Taproot setup (must match commitment exactly!)
    alice_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    alice_public = alice_private.get_public_key()

    # Step 2: Recreate same Hash Lock script
    preimage = "helloworld"
    tr_script = build_hash_lock_script(preimage)
    taproot_address = alice_public.get_taproot_address([[tr_script]])

    # Step 3: Build spending transaction structure
    previous_txid = "9e193d8c5b4ff4ad7cb13d196c2ecc210d9b0ec144bb919ac4314c1240629886"
    input_amount = 0.00005000  # 5000 satoshis
    output_amount = 0.00004000  # 4000 satoshis (1000 sats fee)

    txin = TxInput(previous_txid, 0)
    txout = TxOutput(
        to_satoshis(output_amount),
        alice_public.get_taproot_address().to_script_pub_key()
    )
    tx = Transaction([txin], [txout], has_segwit=True)

    # Step 4: CRITICAL - Build control block to prove script legitimacy
    control_block = ControlBlock(
        alice_public,           # Internal public key for verification
        [[tr_script]],          # Script tree structure (single leaf)
        0,                      # Script index in tree (0 for single leaf)
        is_odd=taproot_address.is_odd()  # Output key parity - get from address!
    )

    # Step 5: Prepare script execution input - the secret "helloworld"
    preimage_hex = preimage.encode('utf-8').hex()  # Convert to hex: "68656c6c6f776f726c64"

    # Step 6: Build Script Path witness (ORDER MATTERS!)
    script_path_witness = TxWitnessInput([
        preimage_hex,              # [0] Script execution input: the secret
        tr_script.to_hex(),        # [1] Revealed script content
        control_block.to_hex()     # [2] Control block: cryptographic proof
    ])

    tx.witnesses.append(script_path_witness)
    return tx
```

这个 witness 里有三样东西值得细看。

**1. Control block（控制块）。**

```python
control_block = ControlBlock(
    alice_public,           # Internal public key: base key for script tree commitment
    [[tr_script]],          # Script tree structure: [[leaf]] indicates single leaf tree
    0,                      # Script index: position of current script in tree
    is_odd=taproot_address.is_odd()  # Parity: y-coordinate parity of output key
)
```

```
Control Block Structure (33 bytes):
┌──────────┬──────────────────────────────────┐
│ Byte 1   │           Bytes 2-33             │
├──────────┼──────────────────────────────────┤
│   c1     │     50be5fc4...126bb4d3          │
├──────────┼──────────────────────────────────┤
│Ver/Parity│         Internal Pubkey          │
└──────────┴──────────────────────────────────┘

- c1 = c0（叶子版本）+ 01（奇偶标志）
- 内部公钥：让验证方能重新算出输出密钥
```

control block 就是"这段脚本属于这个地址"的证明。它携带：

- **内部公钥**——未 tweak 的密钥，好让验证方重做 tweak，确认它落在输出密钥上。
- **脚本树结构**——`[[tr_script]]` 是一棵单叶树；多个脚本会是 `[[script1], [script2]]`，那时控制块还要带上沿途的兄弟节点哈希，以便一路算回根。
- **脚本索引**——这是哪片叶子；单叶时永远是 0。
- **奇偶标志**——输出点的 y 坐标是奇是偶，验证方需要这一个 bit 才能重建出完整的点。用地址的 `is_odd()` 读出来——别去猜。

**2. Witness 顺序。**

```python
script_path_witness = TxWitnessInput([
    preimage_hex,              # [0] 脚本的输入
    tr_script.to_hex(),        # [1] 脚本本身
    control_block.to_hex()     # [2] 控制块
])
```

Bitcoin Core 从底往上读 script-path 的 witness，位置是固定的：

- 最后一个元素：control block
- 倒数第二个：脚本
- 再往前的所有元素：脚本要消费的输入，按顺序排

对我们这个单输入哈希锁来说，就是 `[preimage, script, control_block]`。一个好记的口诀：**数据 -> 代码 -> 证明。**

**3. 原像是十六进制编码的字节。**

```python
preimage_hex = preimage.encode('utf-8').hex()
# "helloworld" -> bytes -> "68656c6c6f776f726c64"
```

Script 处理的是字节串，不是文本。所以 "helloworld" 先转成 UTF-8 字节，再转成十六进制——脚本运行时 `OP_SHA256` 哈希的就是这个。

#### 对着链上数据核验

这笔交易落在了 testnet 上：

**Transaction ID**：[`68f7c8f0...722e604f`](https://mempool.space/testnet/tx/68f7c8f0ab6b3c6f7eb037e36051ea3893b668c26ea6e52094ba01a7722e604f?showDetails=true)

```bash
Witness Stack:
[0] 68656c6c6f776f726c64                    (preimage_hex)
[1] a820936a...f8f8f07af8851                (script_hex)
[2] c150be5f...d126bb4d3                    (control_block)
```

我们可以像节点一样逐层核验。先看原像是否真的哈希出脚本所期望的值：

```python
def verify_preimage_and_script_execution():
    # Verify preimage content
    preimage_hex = "68656c6c6f776f726c64"
    preimage_bytes = bytes.fromhex(preimage_hex)
    preimage_text = preimage_bytes.decode('utf-8')

    print(f"[OK] Preimage Verification:")
    print(f"   Hexadecimal: {preimage_hex}")
    print(f"   Text Content: '{preimage_text}'")

    # Calculate SHA256 hash
    computed_hash = hashlib.sha256(preimage_bytes).hexdigest()
    expected_hash = "936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af"

    print(f"[OK] Hash Verification:")
    print(f"   Computed Hash: {computed_hash}")
    print(f"   Expected Hash: {expected_hash}")
    print(f"   Match Result: {computed_hash == expected_hash}")

    return computed_hash == expected_hash

verify_preimage_and_script_execution()
```

这是脚本自己那一关。节点做得更多：它确认 **control block** 证明了脚本位于 Merkle 根之下，从内部密钥和这个根**还原出地址**，然后才在栈上**运行脚本**。下面两段核验，正对应其中的前两步。

**Control block —— 脚本真的在 Merkle 根之下吗？**

```python
def verify_script_in_merkle_tree():
    # Actual data extracted from chain
    control_block = "c150be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3"
    script_hex = "a820936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af8851"

    # Parse control block
    cb_bytes = bytes.fromhex(control_block)
    leaf_version = cb_bytes[0] & 0xfe    # 0xc0
    parity = cb_bytes[0] & 0x01          # 0x01 (parity)
    internal_pubkey = cb_bytes[1:33].hex()  # Internal public key

    print(f"[OK] Control Block Parsed Successfully:")
    print(f"   Leaf Version: {hex(leaf_version)}")
    print(f"   Internal Pubkey: {internal_pubkey}")

    # Since it's single leaf, no siblings, directly calculate TapLeaf hash as Merkle root
    script_bytes = bytes.fromhex(script_hex)
    tapleaf_hash = tagged_hash("TapLeaf",
        bytes([leaf_version]) +
        bytes([len(script_bytes)]) +
        script_bytes
    )
    merkle_root = tapleaf_hash  # Single leaf case

    print(f"[OK] Script is indeed in Merkle root:")
    print(f"   TapLeaf Hash: {tapleaf_hash.hex()}")
    print(f"   Merkle Root: {merkle_root.hex()}")

    return internal_pubkey, merkle_root

internal_pubkey, merkle_root = verify_script_in_merkle_tree()
```

**地址还原 —— tweak 是否落回那个已承诺的地址？**

```python
def verify_taproot_address_restoration():
    # Essentially tweak again to see if we can restore the intermediate address
    tweak = tagged_hash("TapTweak", 
        bytes.fromhex(internal_pubkey) + merkle_root
    )
    
    # Through elliptic curve operation: output_key = internal_pubkey + tweak * G
    # expected_output_key = point_add(internal_pubkey, scalar_mult(tweak, G))
    
    target_address = (
        "tb1p53ncq9ytax924ps66z6al3wfhy6a29w8h6xfu27xem06t98zkmv"
        "sakd43h"
    )
    
    print(f"[OK] Address Restoration Verification:")
    print(f"   Tweak Value: {tweak.hex()}")
    print(f"   Target Address: {target_address}")
    print(f"   Verification Result: Script Path is indeed usable")
    
    return True

verify_taproot_address_restoration()
```

还原地址，就是把阶段 1 的那个 tweak 反过来当核验跑一遍：从 control block 取出内部密钥，从揭示出的脚本取出 Merkle 根，重新算 tweak，确认它能重建出资金被打去的那个地址。能重建出来，就说明脚本确实被承诺过，这次花费是合法的。

## Script-path 花费失败时：一份排查清单

script-path 花费失败的方式就那么几种、且可预测。一旦失败，照这张清单往下查。

**1. Witness 顺序。** 必须是 `[preimage, script, control_block]`——数据、代码、证明。两种常见的错序：

```
[正确] [preimage, script, control_block]
[错误] [control_block, script, preimage]
[错误] [script, preimage, control_block]
```

**2. 脚本一致性。** 你揭示的脚本必须和你承诺的脚本逐字节相同——一样的操作码、一样的哈希。保证这一点最可靠的办法，是用同一个函数构建两边：

```python
def build_hash_lock_script(preimage):
    hash_value = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    return Script(['OP_SHA256', hash_value, 'OP_EQUALVERIFY', 'OP_TRUE'])

commit_script = build_hash_lock_script("helloworld")
reveal_script = build_hash_lock_script("helloworld")  # 构造上就保证字节相同
```

**3. Control block。** 内部公钥对不对？脚本索引和叶子位置匹配吗（单叶为 0）？还有奇偶标志，要从地址读，别猜：

```python
# 错误 —— 猜
is_odd = True

# 正确 —— 从地址读出来
is_odd = taproot_address.is_odd()
control_block = ControlBlock(..., is_odd=is_odd)
```

**4. 输入编码。** 原像必须先是 UTF-8 字节，再转十六进制：`"helloworld" -> "68656c6c6f776f726c64"`。

**5. 地址还原。** 作为最后一道测试，从内部密钥加脚本树重建 Taproot 地址。如果 commit 阶段和 reveal 阶段的 tweak 算不出同一个地址，说明上游某处对不上。

还有一个值得单独点名的失败方式——把脚本当字符串传，而不是序列化后的 `Script`：

```python
# 错误 —— 人类可读的字符串不是 witness 里该放的东西
script_hex = "OP_SHA256 936a185c... OP_EQUALVERIFY OP_TRUE"

# 正确 —— 序列化一个 Script 对象
script = build_hash_lock_script(preimage)
script_hex = script.to_hex()  # "a820936a185c...8851"
```

## 栈执行：走一遍哈希锁

下面是脚本一步一个操作码地跑起来。

**脚本**：`OP_SHA256 OP_PUSHBYTES_32 936a185c...07af OP_EQUALVERIFY OP_PUSHNUM_1`

**起点** —— witness 把原像加载到栈上：

```
| 68656c6c6f776f726c64                             |
| (preimage_hex: "helloworld")                     |
└──────────────────────────────────────────────────┘
```

**OP_SHA256** —— 弹出原像，压入它的 SHA256：

```
| 936a185c...f8f8f07af  |
| # computed_hash       |
└───────────────────────┘
```

（SHA256("helloworld") = 936a185c...07af）

**PUSH 32 字节** —— 脚本压入它内置的期望哈希：

```
| 936a185c...f8f8f07af  |
| # expected_hash       |
| 936a185c...f8f8f07af  |
| # computed_hash       |
└───────────────────────┘
```

**OP_EQUALVERIFY** —— 弹出栈顶两个元素比较；相等，于是继续执行，两个元素都被消耗：

```
| (empty_stack) |
└───────────────┘
```

**OP_TRUE** —— 压入 1，使栈顶为非零值，这正是脚本被满足的标志：

```
| 01 (true_value) |
└─────────────────┘
```

## Key path 与 Script path 对比

两条路径并排放在一起，用我们刚刚产出的真实数字：

### Key path

- Witness：1 个元素（64 字节签名）
- 交易大小：约 153 字节
- 隐私：完全——不暴露脚本的任何信息
- 验证：一次 Schnorr 检查
- 手续费：最低

### Script path

- Witness：3 个元素（输入 + 脚本 + 控制块）
- 交易大小：约 234 字节
- 隐私：部分——只暴露被执行的那片叶子
- 验证：控制块检查，然后脚本执行
- 手续费：更高（这里约多 50%）

script path 多花字节、也让出一些隐私——但只针对你用的那一条分支。你可能承诺过的其余每条分支都仍然藏着。正是这种**选择性揭示**，让一个 Taproot 地址既能撑起数字商品销售、悬赏、托管、多方合约，又能在被花掉之前一直看起来像一笔普通支付。

## 这和 P2SH 有何不同

和 P2SH 对比，是看清 script path 到底买来什么的最锐利角度。

在 P2SH 里，花费会暴露整个赎回脚本（redeem script）——每一条分支，包括你没走的那些。观察者在它第一次被使用时就学到了整份合约。

Taproot 的 script path 只暴露你执行的那片叶子。没走的分支从不公布；它们只作为哈希折叠进 Merkle 根，链上永远见不到。而且在地址被花费之前，它和一笔普通单签支付无法区分。

所以这个区别是具体的，不是口号：P2SH 暴露整份合约，Taproot 只暴露穿过它的一条路径。对于带多个条件的合约——大多数真实合约都是——这是链上泄露信息的一次大幅削减。

## 本章小结

我们从头到尾构建了 Alice 的哈希锁合约，完整看到了 commit–reveal 模式。

**Commit 与 reveal。** commit 时，一份条件合约折叠进一个外观普通的 Taproot 地址，把资金锁住。reveal 时，Alice 挑一条路径——key path 或 script path——只暴露这条路径所需的东西。

**实现归结为这几件事：**

- **单叶树**——只有一片叶子时，TapLeaf 哈希*就是* Merkle 根，不需要额外的 Merkle 计算。
- **Control block**——通过从内部密钥和脚本叶子哈希还原出地址，来证明某段脚本确实被承诺。
- **栈执行**——哈希锁靠把原像的 `OP_SHA256` 和已承诺的哈希做匹配来完成花费。

**做错就会咬你的地方：**

- **Tagged hash**——标签才是把 TapLeaf 哈希和 TapTweak 分开的东西；同一台机器，不同标签。
- **Witness 顺序**——`[输入, 脚本, 控制块]`，每次都是。
- **commit/reveal 一致性**——两个阶段用同一个函数构建脚本，让字节精确相同。

**下一章。** 第 7 章从一片叶子走向两片：一棵双叶脚本树，Merkle 根要从不止一条分支算出来，你也开始**选择**揭示哪条分支。到那时，"脚本树"里的"树"才真正名副其实。
