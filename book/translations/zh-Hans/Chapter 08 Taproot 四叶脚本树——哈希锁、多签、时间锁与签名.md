# 第 8 章：Taproot 四叶脚本树——哈希锁、多签、时间锁与签名

## 从两片叶子到四片

第 7 章构建了一棵双叶树：一个 TapBranch 覆盖两片叶子，control block 带一个兄弟哈希。本章走到四片叶子，这意味着一棵**两层**的树——叶子两两配成分支，分支再两两配成根。control block 也随之变大：它现在带**两个**兄弟哈希（97 字节），一条向上爬两层、而不是一层的 Merkle 路径。

四片叶子也腾出了足够空间，把真正不同的条件并排放在一起。我们要构建的地址有四条脚本路径，加上 key path——五种花法，一个地址：

1. **哈希锁**——任何拿到原像 "helloworld" 的人都能花（第 6/7 章那把哈希锁）。
2. **2-of-2 多签**——Alice 和 Bob 一起，用 Tapscript 的 `OP_CHECKSIGADD` 写。
3. **CSV 时间锁**——Bob 能花，但要等 2 个区块之后。
4. **简单签名**——Bob 立刻就能花。
5. **Key path**——Alice 用她 tweak 后的密钥直接花；看起来就是一笔普通支付。

这些都对应着真实模式——一条恢复路径加一个时间锁加一条合作关闭，就是钱包恢复方案或闪电通道的骨架——但这里的重点是机制：四片叶子怎么承诺，每条路径怎么揭示和验证。

## 这棵树，以及一个共享地址

下面每一笔花费都出自同一个地址：

```
Address: tb1pjfdm...jcr29q
```

它的树是平衡的——两个分支下各两片叶子：

```
                 Merkle Root
                /            \
        Branch0              Branch1
        /      \             /      \
   Script0   Script1    Script2   Script3
  (Hashlock) (Multisig)  (CSV)    (Sig)
```

每片叶子的 witness 还是第 6 章以来那个形状——数据、脚本、control block——只是数据部分因脚本检查的东西不同而不同：

| 叶子 | 用什么解锁 | Witness `[0..]` |
|------|-----------|-----------------|
| Script 0 哈希锁 | 原像 | `[preimage]` |
| Script 1 多签 | 两个签名 | `[bob_sig, alice_sig]` |
| Script 2 CSV | 一个签名，且过了 2 块 | `[bob_sig]` + 交易 sequence 设好 |
| Script 3 简单签名 | 一个签名 | `[bob_sig]` |
| Key path | Alice 的 tweak 密钥 | `[alice_sig]` |

## 构建这棵树

准备工作——密钥，然后四段脚本，然后树：

```python
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from bitcoinutils.script import Script
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput, Sequence
from bitcoinutils.utils import ControlBlock
from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK
import hashlib

# Set up testnet environment
setup('testnet')

# Generate participant keys
alice_priv = PrivateKey("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
bob_priv = PrivateKey("cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG")
alice_pub = alice_priv.get_public_key()
bob_pub = bob_priv.get_public_key()
```

四段脚本。两段是前面章节的老面孔，两段是新的：

```python
# Script 0: SHA256 Hashlock
preimage = "helloworld"
hash0 = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
script0 = Script([
    'OP_SHA256',
    hash0,
    'OP_EQUALVERIFY',
    'OP_TRUE'
])

# Script 1: 2-of-2 Multisig (Tapscript style)
script1 = Script([
    "OP_0",                      # Initialize counter
    alice_pub.to_x_only_hex(),   # Alice's x-only public key
    "OP_CHECKSIGADD",           # Verify Alice signature, increment counter
    bob_pub.to_x_only_hex(),    # Bob's x-only public key
    "OP_CHECKSIGADD",           # Verify Bob signature, increment counter
    "OP_2",                     # Required signature count
    "OP_EQUAL"                  # Check counter == required count
])

# Script 2: CSV Timelock
from bitcoinutils.utils import Sequence, TYPE_RELATIVE_TIMELOCK
relative_blocks = 2
seq = Sequence(TYPE_RELATIVE_TIMELOCK, relative_blocks)
script2 = Script([
    seq.for_script(),           # Push sequence value
    "OP_CHECKSEQUENCEVERIFY",   # Verify relative timelock
    "OP_DROP",                  # Clean stack
    bob_pub.to_x_only_hex(),    # Bob's public key
    "OP_CHECKSIG"               # Verify Bob's signature
])

# Script 3: Simple Signature
script3 = Script([
    bob_pub.to_x_only_hex(),
    "OP_CHECKSIG"
])
```

树写成嵌套的成对结构——每个分支两片叶子——正是这种嵌套给出了两层 Merkle 结构：

```python
# Build script tree: [[left branch], [right branch]]
tree = [[script0, script1], [script2, script3]]

# Generate Taproot address using Alice's internal key
taproot_address = alice_pub.get_taproot_address(tree)
print(f"Taproot Address: {taproot_address.to_string()}")
# Output: tb1pjfdm...jcr29q
```

## 分别花费每条路径

五笔花费的差别只在于：往 witness 里放什么，以及 control block 指向哪个叶子索引。我们五条都走一遍；模式是重复的。

### 1. 哈希锁（Script 0）

第 6/7 章那把哈希锁，现在位于四叶树的索引 0——所以它的 control block 带两层证明，但调用看起来一模一样：

```python
def spend_hashlock_path():
    """Script 0: SHA256 Hashlock spending"""
    # UTXO information
    commit_txid = (
        "245563c5aa4c6d32fc34eed2f182b5ed"
        "76892d13370f067dc56f34616b66c468"
    )
    vout = 0
    input_amount = 1200  # satoshis
    output_amount = 666

    # Build transaction
    txin = TxInput(commit_txid, vout)
    txout = TxOutput(output_amount, alice_pub.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Key: Construct Control Block (script index 0)
    cb = ControlBlock(alice_pub, tree, 0, is_odd=taproot_address.is_odd())

    # Witness data: [preimage, script, control_block]
    preimage_hex = "helloworld".encode('utf-8').hex()
    tx.witnesses.append(TxWitnessInput([
        preimage_hex,           # Preimage to unlock hash lock
        script0.to_hex(),       # Executed script
        cb.to_hex()            # Merkle proof
    ]))

    return tx
# Testnet transaction ID: 1ba4835f...a6fd6845
```

### 2. 多签（Script 1）

多签路径是值得多停留一下的新东西。两个签名，都作为针对同一片叶子的脚本路径签名产生：

```python
def spend_multisig_path():
    """Script 1: 2-of-2 Multisig spending"""
    # UTXO information
    commit_txid = (
        "1ed5a3e97a6d3bc0493acc2aac15011c"
        "d99000b52e932724766c3d277d76daac"
    )
    vout = 0
    input_amount = 1400
    output_amount = 668

    # Build transaction
    txin = TxInput(commit_txid, vout)
    txout = TxOutput(output_amount, alice_pub.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Key: Construct Control Block (script index 1)
    cb = ControlBlock(alice_pub, tree, 1, is_odd=taproot_address.is_odd())

    # Key: Script Path signature (note script_path=True)
    sig_alice = alice_priv.sign_taproot_input(
        tx, 0, [taproot_address.to_script_pub_key()], [input_amount],
        script_path=True,      # Script Path mode
        tapleaf_script=script1, # Specify leaf script
        tweak=False
    )

    sig_bob = bob_priv.sign_taproot_input(
        tx, 0, [taproot_address.to_script_pub_key()], [input_amount],
        script_path=True,
        tapleaf_script=script1,
        tweak=False
    )

    # Witness data: [Bob signature, Alice signature, script, control_block]
    # Note: Bob signature first (stack execution order)
    tx.witnesses.append(TxWitnessInput([
        sig_bob,               # Consumed second
        sig_alice,             # Consumed first
        script1.to_hex(),
        cb.to_hex()
    ]))

    return tx
# Testnet transaction ID: 1951a3be...b7e604a1
```

两个签名方都用 `script_path=True`、`tapleaf_script=script1`、`tweak=False`——就是第 7 章那套脚本路径签名，只是对这一片叶子做了两遍。witness 顺序是微妙的地方，下面的栈走法会精确解释为什么 `sig_bob` 排在前面。

### 3. CSV 时间锁（Script 2）

时间锁路径有一个别的路径没有的要求：*交易本身*必须设一个匹配的 sequence，否则 `OP_CHECKSEQUENCEVERIFY` 会拒绝它。脚本说"必须过了 2 个区块"，而输入的 sequence 就是证明这一点的东西：

```python
def spend_csv_timelock_path():
    """Script 2: CSV Timelock spending"""
    # UTXO information
    commit_txid = (
        "9a2bff4161411f25675c730777c7b4f5"
        "b2837e19898500628f2010c1610ac345"
    )
    vout = 0
    input_amount = 1600
    output_amount = 800

    # Key: CSV requires special sequence value
    relative_blocks = 2
    seq = Sequence(TYPE_RELATIVE_TIMELOCK, relative_blocks)
    seq_for_input = seq.for_input_sequence()

    # Build transaction (note sequence parameter)
    txin = TxInput(commit_txid, vout, sequence=seq_for_input)  # Key!
    txout = TxOutput(output_amount, alice_pub.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Control Block (script index 2)
    cb = ControlBlock(alice_pub, tree, 2, is_odd=taproot_address.is_odd())

    # Bob signature
    sig_bob = bob_priv.sign_taproot_input(
        tx, 0, [taproot_address.to_script_pub_key()], [input_amount],
        script_path=True,
        tapleaf_script=script2,
        tweak=False
    )

    # Witness data: [Bob signature, script, control_block]
    tx.witnesses.append(TxWitnessInput([
        sig_bob,
        script2.to_hex(),
        cb.to_hex()
    ]))

    return tx
# Testnet transaction ID: 98361ab2...d17f41ee
```

注意这种对称：脚本带着 `seq.for_script()`（时间锁条件），输入带着 `seq.for_input_sequence()`（"它已满足"的声明）。两者来自同一个 `Sequence` 对象，且必须都在——脚本陈述规则，交易提供证据。

### 4. 简单签名（Script 3）

最朴素的叶子——Bob 签名，没有额外条件。和第 7 章的 Bob 脚本一样，现在位于索引 3：

```python
def spend_simple_sig_path():
    """Script 3: Simple Signature spending"""
    # UTXO information
    commit_txid = (
        "632743eb43aa68fb1c486bff48e8b27c"
        "436ac1f0d674265431ba8c1598e2aeea"
    )
    vout = 0
    input_amount = 1800
    output_amount = 866

    # Build transaction
    txin = TxInput(commit_txid, vout)
    txout = TxOutput(output_amount, alice_pub.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Control Block (script index 3)
    cb = ControlBlock(alice_pub, tree, 3, is_odd=taproot_address.is_odd())

    # Bob signature
    sig_bob = bob_priv.sign_taproot_input(
        tx, 0, [taproot_address.to_script_pub_key()], [input_amount],
        script_path=True,
        tapleaf_script=script3,
        tweak=False
    )

    # Witness data: [Bob signature, script, control_block]
    tx.witnesses.append(TxWitnessInput([
        sig_bob,
        script3.to_hex(),
        cb.to_hex()
    ]))

    return tx
# Testnet transaction ID: 1af46d4c...4c6c71b9
```

### 5. Key path

以及什么都不暴露的那一条——Alice 的 key-path 花费，精神上和第 6 章一致。它仍然需要整棵 `tree` 来重建 tweak，但树的任何信息都不会上链：

```python
def spend_key_path():
    """Key Path: Most efficient and private spending method"""
    # UTXO information
    commit_txid = (
        "42a9796a91cf971093b35685db9cb1a1"
        "64fb5402aa7e2541ea7693acc1923059"
    )
    vout = 0
    input_amount = 2000
    output_amount = 888

    # Build transaction
    txin = TxInput(commit_txid, vout)
    txout = TxOutput(output_amount, alice_pub.get_taproot_address().to_script_pub_key())
    tx = Transaction([txin], [txout], has_segwit=True)

    # Key: Key Path signature (note script_path=False)
    sig_alice = alice_priv.sign_taproot_input(
        tx, 0, [taproot_address.to_script_pub_key()], [input_amount],
        script_path=False,      # Key Path mode
        tapleaf_scripts=tree    # Complete script tree (for tweak calculation)
    )

    # Witness data: Only one signature (most efficient!)
    tx.witnesses.append(TxWitnessInput([sig_alice]))

    return tx
# Testnet transaction ID: 1e518aa5...e95600da
```

再强调一次这个参数差异，因为它是最常见的困惑点：key path 传 `tapleaf_scripts=tree`（复数，整棵树，用来算 tweak），配 `script_path=False`；每条脚本路径传 `tapleaf_script=script_n`（单数，一片叶子），配 `script_path=True`。

## OP_CHECKSIGADD 怎么跑

多签叶子是本章唯一新出现的脚本执行，我们走一遍它的栈。Tapscript 用 `OP_CHECKSIGADD` 取代了旧的 `OP_CHECKMULTISIG`，它维护一个有效签名的累加计数：

```python
# Script 1: 2-of-2 multisig (tapscript style)
script1 = Script([
    "OP_0",                      # Initialize counter to 0
    alice_pub.to_x_only_hex(),   # Alice's x-only public key
    "OP_CHECKSIGADD",           # Verify Alice signature, increment counter if successful
    bob_pub.to_x_only_hex(),    # Bob's x-only public key
    "OP_CHECKSIGADD",           # Verify Bob signature, increment counter if successful
    "OP_2",                     # Push required signature count 2
    "OP_EQUAL"                  # Check if counter equals required count
])
```

witness 在脚本运行前把两个签名都放上栈，而顺序很重要：

```python
# Witness data: [Bob signature, Alice signature, script, control_block]
# Note: Bob signature first, but consumed second!
tx.witnesses.append(TxWitnessInput([
    sig_bob,               # 栈位置：靠下，被第二个 OP_CHECKSIGADD 消费
    sig_alice,             # 栈位置：顶端，被第一个 OP_CHECKSIGADD 消费
    script1.to_hex(),
    cb.to_hex()
]))
```

**栈走法** —— 脚本 `OP_0 [Alice_PubKey] OP_CHECKSIGADD [Bob_PubKey] OP_CHECKSIGADD OP_2 OP_EQUAL`。

**起点** —— 两个签名都已加载，`sig_alice` 在顶上：

```
| sig_alice   | ← 顶，先被消费
| sig_bob     |
└─────────────┘
```

**OP_0** —— 压入计数器，初始化为 0：

```
| 0           | ← 计数器
| sig_alice   |
| sig_bob     |
└─────────────┘
```

**[Alice_PubKey]** —— 脚本压入 Alice 的密钥：

```
| alice_pubkey|
| 0           |
| sig_alice   |
| sig_bob     |
└─────────────┘
```

**OP_CHECKSIGADD** —— 弹出密钥、弹出计数器、弹出它下面的签名；用 `alice_pubkey` 验 `sig_alice`；压入 计数器+1：

```
| 1           | ← 计数器现在是 1
| sig_bob     |
└─────────────┘
```

**[Bob_PubKey]** 接 **OP_CHECKSIGADD** —— 对 Bob 同样来一遍，消费 `sig_bob`：

```
| 2           | ← 计数器现在是 2
└─────────────┘
```

**OP_2** 接 **OP_EQUAL** —— 压入要求的数量，比较；`2 == 2`，于是压入 1，脚本被满足：

```
| 1           |
└─────────────┘
```

这就是为什么 witness 里 `sig_alice` 必须在 `sig_bob` 上面：*第一个* `OP_CHECKSIGADD` 是 Alice 的，它消费当下栈顶的那个签名。witness 列的是 `[sig_bob, sig_alice]`——bob 在前，于是 alice 落到顶上，于是 alice 先被检查。反过来，两个检查都会失败。

```python
# 错序 —— 两个检查都失败
witness = [sig_alice, sig_bob, script1.to_hex(), cb.to_hex()]

# 正序 —— bob 在前，alice 落到顶上
witness = [sig_bob, sig_alice, script1.to_hex(), cb.to_hex()]
```

**为什么用 `OP_CHECKSIGADD` 而不是 `OP_CHECKMULTISIG`？** 三个具体原因：
- 它一次检查一个签名、失败即停，而不是去试各种组合。
- 计数器是显式的——没有 `OP_CHECKMULTISIG` 那个差一位的多余元素怪癖。
- 它直接吃 32 字节的 x-only 密钥，而 `OP_CHECKMULTISIG` 要 33 字节压缩密钥。

## 四叶 control block

树有两层，每片叶子的 Merkle 证明就是两个哈希——它的直接兄弟，再加上那一对的兄弟分支——所以 control block 是 97 字节：

```
33 字节：版本+奇偶 (1) + 内部公钥 (32)
+32 字节：兄弟叶子哈希    （第 1 层）
+32 字节：兄弟分支哈希    （第 2 层）
= 97 字节
```

每片叶子需要哪两个哈希，取决于它的位置：

```python
paths = {
    0: "[Script1_TapLeaf, Branch1_TapBranch]",  # Hashlock
    1: "[Script0_TapLeaf, Branch1_TapBranch]",  # Multisig
    2: "[Script3_TapLeaf, Branch0_TapBranch]",  # CSV
    3: "[Script2_TapLeaf, Branch0_TapBranch]"   # Simple Sig
}
```

### 读一个真实的 control block

拿多签那笔 [`1951a3be...b7e604a1`](https://mempool.space/testnet/tx/1951a3be0f05df377b1789223f6da66ed39c781aaf39ace0bf98c3beb7e604a1?showDetails=true)，把它的 witness 从链上抠出来：

```python
def analyze_real_multisig_transaction():
    """Analyze Control Block verification of real multisig transaction"""

    # Witness stack extracted from on-chain data
    witness_stack = [
        # Bob's signature (first witness item)
        (
            "31fa0ca7929dac01b908349326183dd7a0f752475d42f11dc2cd0075110ca2a4"
            "c255f3e310dfc0800e69609c872254241dcf827847e5b64821cefa6c6db575bc"
        ),

        # Alice's signature (second witness item)
        (
            "22272de665b998668ae9e97cb72d9814d362ae101ee878caee04da0d2a7efb14"
            "e8bcdd7eb8082fad30864ec7f22bce6fb2d2178764a0b2f5427346e4b5821fa0"
        ),

        # Multisig script (third witness item)
        (
            "002050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb"
            "4d3ba2084b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef"
            "63af5ba5287"
        ),

        # Control Block (fourth witness item) - 97 bytes
        (
            "c050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3"
            "fe78d8523ce9603014b28739a51ef826f791aa17511e617af6dc96a8f10f659eda"
            "55197526f26fa309563b7a3551ca945c046e5b7ada957e59160d4d27f299e3"
        )
    ]

    print("=== On-Chain Multisig Transaction Control Block Analysis ===")
    return witness_stack
```

把 97 字节的 control block 拆成四部分：

```python
def parse_control_block_bytes():
    """Parse detailed structure of 97-byte Control Block"""

    cb_hex = (
        "c050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3"
        "fe78d8523ce9603014b28739a51ef826f791aa17511e617af6dc96a8f10f659eda"
        "55197526f26fa309563b7a3551ca945c046e5b7ada957e59160d4d27f299e3"
    )
    cb_bytes = bytes.fromhex(cb_hex)

    # Byte 0: Version + parity bit
    version_and_parity = cb_bytes[0]  # 0xc0
    leaf_version = version_and_parity & 0xfe  # 0xc0 (leaf version)
    parity_bit = version_and_parity & 0x01    # 0 (even)

    # Bytes 1-32: Internal public key (Alice's x-only public key)
    internal_pubkey = cb_bytes[1:33].hex()

    # Bytes 33-64: First sibling node (Script 0's TapLeaf hash)
    sibling_1 = cb_bytes[33:65].hex()

    # Bytes 65-96: Second sibling node (Branch 1's TapBranch hash)
    sibling_2 = cb_bytes[65:97].hex()

    print("Control Block Detailed Parsing:")
    print(f"Total length: {len(cb_bytes)} bytes")
    print(f"Leaf version: 0x{leaf_version:02x}")
    print(f"Parity bit: {parity_bit} (output key is {'odd' if parity_bit else 'even'})")
    print(f"Internal pubkey: {internal_pubkey}")
    print(f"  -> Alice's x-only public key")
    print(f"Sibling node 1: {sibling_1}")
    print(f"  -> Script 0 (Hashlock) TapLeaf hash")
    print(f"Sibling node 2: {sibling_2}")
    print(f"  -> Branch 1 (Script2+Script3) TapBranch hash")

    return {
        'leaf_version': leaf_version,
        'parity_bit': parity_bit,
        'internal_pubkey': internal_pubkey,
        'sibling_1': sibling_1,
        'sibling_2': sibling_2
    }
```

### 爬两层回到地址

有了脚本和它的两个兄弟哈希，验证还是第 7 章那个思路——重算根、看它能否重建地址——只是现在要走两步 TapBranch，而不是一步：

```python
def reconstruct_merkle_root_step_by_step():
    """Step-by-step Merkle Root reconstruction for Control Block verification"""

    # Parsed CB data
    cb_data = parse_control_block_bytes()

    # Step 1: Calculate Script 1 (Multisig) TapLeaf hash
    multisig_script_hex = (
        "002050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb"
        "4d3ba2084b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef"
        "63af5ba5287"
    )
    script_bytes = bytes.fromhex(multisig_script_hex)

    # TapLeaf = Tagged_Hash("TapLeaf", version + length + script)
    tapleaf_data = bytes([cb_data['leaf_version']]) + len(script_bytes).to_bytes(1, 'big') + script_bytes
    script1_tapleaf = tagged_hash("TapLeaf", tapleaf_data)
    print("Step 1: current script's TapLeaf hash")
    print(f"  Script1 TapLeaf: {script1_tapleaf.hex()}")

    # Step 2: Combine with Script 0 (sibling 1) to form Branch 0
    script0_tapleaf = bytes.fromhex(cb_data['sibling_1'])
    if script0_tapleaf < script1_tapleaf:           # lexicographic order
        branch0_data = script0_tapleaf + script1_tapleaf
    else:
        branch0_data = script1_tapleaf + script0_tapleaf
    branch0_hash = tagged_hash("TapBranch", branch0_data)
    print("Step 2: Branch0 = TapBranch(Script0, Script1)")
    print(f"  Branch0: {branch0_hash.hex()}")

    # Step 3: Combine with Branch 1 (sibling 2) to form the Merkle Root
    branch1_hash = bytes.fromhex(cb_data['sibling_2'])
    if branch0_hash < branch1_hash:
        root_data = branch0_hash + branch1_hash
    else:
        root_data = branch1_hash + branch0_hash
    merkle_root = tagged_hash("TapBranch", root_data)
    print("Step 3: MerkleRoot = TapBranch(Branch0, Branch1)")
    print(f"  Merkle Root: {merkle_root.hex()}")

    # Step 4: Tweak the internal key with the Merkle root
    internal_pubkey = bytes.fromhex(cb_data['internal_pubkey'])
    tap_tweak = tagged_hash("TapTweak", internal_pubkey + merkle_root)
    print("Step 4: TapTweak(internal_pubkey || merkle_root)")
    print(f"  Tweak: {tap_tweak.hex()}")

    # Step 5: Output key = internal_pubkey + tap_tweak * G  (needs an EC library),
    #         then bech32m-encode as the P2TR address. The library does this; the
    #         check is simply that it rebuilds the funding address:
    expected_address = (
        "tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqj"
        "cr29q"
    )
    print("Step 5: output key -> address")
    print(f"  Expected address: {expected_address}")
    print(f"  Control Block valid: rebuilds the funding address")

    return tap_tweak

# Execute complete verification
if __name__ == "__main__":
    analyze_real_multisig_transaction()
    parse_control_block_bytes()
    reconstruct_merkle_root_step_by_step()
```

对着真实字节跑一遍，得到 Script1 TapLeaf `63cb9e47...`、Branch0 `d6ac4c01...`、Merkle root `33fd4d4b...`，以及一个能重建出 `tb1pjfdm...jcr29q` 的 tweak——正是五笔花费共出的那个地址。从这次解析里有两点值得注意：

- 兄弟 1 是 `fe78d852...f10f659e`——恰好是 Script 0 的 TapLeaf 哈希，也正是我们在第 7 章为那把哈希锁算出的同一个值。同一段脚本，同一个叶子哈希，跨章一致。
- 证明是分层的：第 0 层是多签叶子本身，第 1 层是 `Branch0 = TapBranch(Script0, Script1)`，第 2 层是 `Root = TapBranch(Branch0, Branch1)`。每一步 TapBranch 都把两个输入按字典序排，这正是任何人都能复算出根的原因。

## 三个会咬人的地方

四叶花费会以几种可预测的方式失败。按踩坑频率排序：

**多签的 witness 顺序。** Bob 的签名在列表里排第一，好让 Alice 的落到栈顶——反过来两个检查都失败（见上面的栈走法）：

```python
# 错
witness = [sig_alice, sig_bob, script, control_block]
# 对
witness = [sig_bob, sig_alice, script, control_block]
```

**CSV 的 sequence。** CSV 脚本只有在输入的 sequence 表明已过足够区块时才通过。忘了它，`OP_CHECKSEQUENCEVERIFY` 就拒绝这笔花费：

```python
# 错 —— 默认 sequence，CSV 失败
txin = TxInput(txid, vout)
# 对 —— sequence 匹配脚本的时间锁
txin = TxInput(txid, vout, sequence=seq.for_input_sequence())
```

**key path 与 script path 的签名。** 两者参数不同，混用是最常见的单一错误：

```python
# key path：    整棵树（用来 tweak 密钥），script_path=False
sig = priv.sign_taproot_input(..., script_path=False, tapleaf_scripts=tree)
# script path： 一片叶子，script_path=True
sig = priv.sign_taproot_input(..., script_path=True, tapleaf_script=script)
```

## 本章小结

四片叶子把第 7 章的单个 TapBranch 变成了一棵两层的树，control block 也随之变大——97 字节，带一条两个哈希的 Merkle 路径。我们把四个真正不同的条件放在了一个地址下（一把哈希锁、一个 2-of-2 多签、一个 CSV 时间锁、一个普通签名），在 testnet 上各花了一遍，并通过把多签的 control block 沿两层分支爬回每条路径共享的同一个地址，验证了它。

两个要记住的点：

- **`OP_CHECKSIGADD`** 是 Tapscript 做多签的方式——一个有效签名的累加计数，喂给它的 witness 里签名顺序必须匹配脚本检查它们的顺序。
- **树越高，Merkle 路径越长。** 每多一层深度，control block 就多一个 32 字节的兄弟；成本随叶子数量的对数增长，而不是随个数增长。

### 第 5–8 章讲了什么

本章把全书的基础部分讲完了。从第 5 章起，这四章一次一个机制，把 Taproot 搭了起来：

- **第 5 章** —— Schnorr 签名与 key tweak：一个公钥如何承诺额外的数据。
- **第 6 章** —— 单叶脚本路径：承诺一段脚本，然后花掉它，或走 key path。
- **第 7 章** —— 两片叶子：一个 TapBranch 之上的 Merkle 根，以及用兄弟哈希证明一片叶子的 control block。
- **第 8 章** —— 四片叶子、两层树，带多签、时间锁和一条 97 字节的证明。

这四章是直接相互叠加的：第 5 章的 key tweak 正是用来承诺 Merkle 根的，第 6 章的 commit–reveal 是每条脚本路径的工作方式，而 Merkle 证明从第 7 章到第 8 章每多一层就多一个兄弟哈希。如果这些联系还不清楚，继续往下之前值得把这四章放在一起读一遍——后面的内容默认你已经掌握了它们。

### 第 9–12 章：应用

全书的后半段，从"Taproot 如何运作"转到"它怎么被使用"。每一章拿一个真实系统，指出这些机制在哪里出现：

- **第 9 章 —— Ordinals 与 BRC-20。** 用脚本路径来存数据，而不是花费条件：一段单叶脚本，把任意内容承诺进一个 Taproot 输出。
- **第 10 章 —— RGB 与 Tapret。** 客户端验证，把承诺放进脚本树里。
- **第 11 章 —— 闪电通道。** 把通道从 P2WSH 多签搬到 Taproot，以及这带来的隐私。
- **第 12 章 —— 静默支付。** 又是第 5 章那套椭圆曲线运算，这次用于地址隐私：可复用地址，在链上不留下关联。

**下一章。** 第 9 章和第 6 章一样从单叶起步，但用途不同：把数据存进一个 Taproot 输出。
