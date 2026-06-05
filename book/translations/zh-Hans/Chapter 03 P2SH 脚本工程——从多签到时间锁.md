# 第 3 章：P2SH 脚本工程——从多签到时间锁

Pay-to-Script-Hash（P2SH）是比特币脚本第一次变得实用的地方：任何脚本，无论多复杂，都能锁在一个 20 字节哈希后面，只在花费时才揭示。本章用 P2SH 搭起后面全书反复出现的两个模式——多签（multisig）和时间锁（time lock）——并把两者都在栈上走一遍。它处在第 2 章的单签 P2PKH 和 Taproot 的脚本树之间。

## 3.1 P2SH 架构：哈希后面的脚本

P2SH 让任何脚本都能用一个紧凑的 20 字节哈希来代表，把脚本的复杂度移出 UTXO 集，推迟到花费时。

### 两阶段验证模型

P2SH 分两个清晰的阶段：

**阶段 1：哈希验证**

```
OP_HASH160 <script_hash> OP_EQUAL
```

**阶段 2：脚本执行**

```
<revealed_script> -> Execute as Bitcoin Script
```

### P2SH 地址生成过程

P2SH 沿用第 1 章讲过的 Hash160 -> Base58Check 流程，只是哈希的是脚本而不是公钥：

```
Script Serialization -> hex_encoded_script
Hash160(script)     -> 20_bytes_script_hash  
Version + Base58Check -> 3...address (mainnet)
```

所有 P2SH 地址在主网以 "3" 开头、测试网以 "2" 开头，一眼就和 P2PKH 地址区分开。

### ScriptSig 构造模式

P2SH 的解锁脚本（ScriptSig）遵循一个固定模式：

```
<script_data> <serialized_redeem_script>
```

其中 `<script_data>` 是满足赎回脚本（redeem script）条件所需的值，`<serialized_redeem_script>` 是原始脚本——它的哈希要和锁定脚本里的哈希匹配。

## 3.2 2-of-3 多签

多签输出需要不止一把密钥才能花。2-of-3——三把里任意两把——是共享托管的常见形态：没有任何一个人能独自动用资金，也不会因为一把密钥丢失就把资金锁死。

### 设定：三把密钥

三方各持一把密钥，任意两方就能授权一次花费：

- **Alice**、**Bob**、**Carol** —— 三把密钥，需要两把。

赎回脚本用 `OP_CHECKMULTISIG` 把这条规则编码进去：

```python
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from bitcoinutils.script import Script
from bitcoinutils.keys import P2shAddress

def create_multisig_p2sh():
    setup('testnet')
    
    # Stakeholder public keys
    alice_pk = '02898711e6bf63f5cbe1b38c05e89d6c391c59e9f8f695da44bf3d20ca674c8519'
    bob_pk = '0284b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5'
    carol_pk = '0317aa89b43f46a0c0cdbd9a302f2508337ba6a06d123854481b52de9c20996011'
    
    # 2-of-3 multisig redeem script
    redeem_script = Script([
        'OP_2',           # Require 2 signatures
        alice_pk,         # Alice's public key
        bob_pk,           # Bob's public key  
        carol_pk,         # Carol's public key
        'OP_3',           # Total of 3 keys
        'OP_CHECKMULTISIG' # Multisig verification
    ])
    
    # Generate P2SH address
    p2sh_addr = P2shAddress.from_script(redeem_script)
    return p2sh_addr, redeem_script
```

### bitcoinutils 函数解析

**`Script([...])` 构造器**：从一个操作码和数据的列表创建 Script 对象。库会自动把 `'OP_2'` 这类操作码编码成它们的字节表示（`0x52`）。

**`P2shAddress.from_script(script)`**：生成 P2SH 地址，步骤是：
1. 把脚本序列化成字节
2. 计算 Hash160(script)
3. 加版本字节（主网 0x05、测试网 0xc4）
4. 做 Base58Check 编码

**脚本序列化**：这个赎回脚本序列化成：

```text
522102898711e6bf63f5cbe1b38c05e89d6c391c59e9f8f695da44bf3d20ca674c8519
210284b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5
210317aa89b43f46a0c0cdbd9a302f2508337ba6a06d123854481b52de9c20996011
53ae
```

逐字节拆开：
- `52`：OP_2
- `21`：压入 33 字节（压缩公钥）
- `02898711...`：Alice 的公钥
- `21`：压入 33 字节
- `0284b595...`：Bob 的公钥
- `21`：压入 33 字节
- `0317aa89...`：Carol 的公钥
- `53`：OP_3
- `ae`：OP_CHECKMULTISIG

### 花费多签 UTXO

当 Alice 和 Bob 决定授权一笔支付时，他们必须按正确顺序提供签名，连同赎回脚本：

```python
def spend_multisig_p2sh():
    # Previous UTXO details
    utxo_txid = '4b869865bc4a156d7e0ba14590b5c8971e57b8198af64d88872558ca88a8ba5f'
    utxo_vout = 0
    utxo_amount = 0.00001600  # 1,600 satoshis
    
    # Create transaction
    txin = TxInput(utxo_txid, utxo_vout)
    txout = TxOutput(to_satoshis(0.00000888), recipient_address.to_script_pub_key())
    tx = Transaction([txin], [txout])
    
    # Sign with Alice and Bob's keys
    alice_sig = alice_sk.sign_input(tx, 0, redeem_script)
    bob_sig = bob_sk.sign_input(tx, 0, redeem_script)
    
    # Construct ScriptSig
    txin.script_sig = Script([
        'OP_0',                    # OP_CHECKMULTISIG bug workaround
        alice_sig,                 # First signature
        bob_sig,                   # Second signature  
        redeem_script.to_hex()     # Reveal the redeem script
    ])
```

### bitcoinutils 签名函数

**`private_key.sign_input(tx, input_index, script)`**：为某个交易输入创建一个 ECDSA 签名，用传入的脚本计算签名哈希。对 P2SH 输入，这个 script 参数应当是赎回脚本。

**`script.to_hex()`**：把 Script 对象序列化成十六进制字节表示，在脚本执行时作为数据压入栈。

### 多签栈执行分析

我们用真实交易数据把整个脚本执行走一遍，跟着 Bitcoin Core 的两阶段 P2SH 执行：

**Transaction ID**：[`e68bef53...ba0fd4e0`](https://mempool.space/testnet/tx/e68bef534c7536300c3ae5ccd0f79e031cab29d262380a37269151e8ba0fd4e0?showDetails=true)

## 阶段 1：ScriptSig + ScriptPubKey 执行

**初始状态：**

```
│ (empty)                                │
└────────────────────────────────────────┘
```

### 1. PUSH OP_0：多签 bug 的补丁
比特币的 OP_CHECKMULTISIG 有个已知的差一位 bug，会多弹出一个栈元素。压入一个 OP_0 来补偿。

```
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

### 2. PUSH Alice 的签名：第一个授权

```
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

### 3. PUSH Bob 的签名：第二个授权  

```
│ 3044022065f8...fd9e01 (bob_sig)        │
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

### 4. PUSH 赎回脚本：揭示花费条件

```
│ 522102898711...601153ae (redeem_script)  │
│ 3044022065f8...fd9e01 (bob_sig)          │
│ 30440220694f...7a6501 (alice_sig)        │
│ 00 (op_zero)                             │
└──────────────────────────────────────────┘
```

### 5. OP_HASH160：验证脚本哈希匹配
执行 P2SH 锁定脚本 `OP_HASH160 <script_hash> OP_EQUAL`：

```
│ dd81b5beb3d8...5cb0ca (computed_hash)    │
│ 3044022065f8...fd9e01 (bob_sig)          │
│ 30440220694f...7a6501 (alice_sig)        │
│ 00 (op_zero)                             │
└──────────────────────────────────────────┘
```

### 6. PUSH 期望哈希：来自锁定脚本

```
│ dd81b5beb3d8...5cb0ca (expected_hash)    │
│ dd81b5beb3d8...5cb0ca (computed_hash)    │
│ 3044022065f8...fd9e01 (bob_sig)          │
│ 30440220694f...7a6501 (alice_sig)        │
│ 00 (op_zero)                             │
└──────────────────────────────────────────┘
```

### 7. OP_EQUAL：确认哈希匹配

```
│ 1 (true)                               │
│ 3044022065f8...fd9e01 (bob_sig)        │
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

**（阶段 1 完成：哈希验证成功）**

## P2SH 切换：栈重置机制

**关键点**：Bitcoin Core 识别出 P2SH 模式，切换到第二个验证阶段，做法是：

1. **检测 P2SH 模式**：`OP_HASH160 <hash> OP_EQUAL`
2. **重置栈**：回到 scriptSig 执行后的状态（丢弃 TRUE）
3. **取出赎回脚本**：从原始 scriptSig 数据里
4. **准备干净的执行**：给赎回脚本配上签名数据

**栈重置回 ScriptSig 后状态：**

```
│ 3044022065f8...fd9e01 (bob_sig)        │
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

**（TRUE 被丢弃——赎回脚本从干净的栈开始）**

## 阶段 2：赎回脚本执行

Bitcoin Core 现在执行赎回脚本：`OP_2 alice_pk bob_pk carol_pk OP_3 OP_CHECKMULTISIG`

### 8. OP_2：压入要求的签名数

```
│ 2 (required_sigs)                      │
│ 3044022065f8...fd9e01 (bob_sig)        │
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

### 9-11. PUSH 公钥：加载验证密钥

```
│ 0317aa89b43f...996011 (carol_pk)       │
│ 0284b5951609...eef63af5 (bob_pk)       │
│ 02898711e6bf...674c8519 (alice_pk)     │
│ 2 (required_sigs)                      │
│ 3044022065f8...fd9e01 (bob_sig)        │
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

### 12. OP_3：压入密钥总数

```
│ 3 (total_keys)                         │
│ 0317aa89b43f...996011 (carol_pk)       │
│ 0284b5951609...eef63af5 (bob_pk)       │
│ 02898711e6bf...674c8519 (alice_pk)     │
│ 2 (required_sigs)                      │
│ 3044022065f8...fd9e01 (bob_sig)        │
│ 30440220694f...7a6501 (alice_sig)      │
│ 00 (op_zero)                           │
└────────────────────────────────────────┘
```

### 13. OP_CHECKMULTISIG：验证签名
这个操作码消费：
- 密钥数（3）
- 公钥（Alice、Bob、Carol）
- 签名数（2）
- 签名（Alice 的、Bob 的）
- 多余的一项（OP_0，因为那个 bug）

验证过程：
1. Alice 的签名用 Alice 的公钥验证通过 [OK]
2. Bob 的签名用 Bob 的公钥验证通过 [OK]
3. 满足所需门限（2-of-3）[OK]

### 最终状态：多签验证完成

```
│ 1 (true)                               │
└────────────────────────────────────────┘
```

**（P2SH 执行成功：干净的两阶段验证）**

## 3.3 用 CSV 做时间锁

CheckSequenceVerify（CSV）强制一个相对时间锁：花费被推迟若干个区块，从 UTXO 创建那一刻起算。下面是一个真实的 testnet 实现。

### 一个 3 区块时间锁

**Transaction ID**：[`34f5bf0c...0861906f`](https://mempool.space/testnet/tx/34f5bf0cf328d77059b5674e71442ded8cdcfc723d0136733e0dbf180861906f?showDetails=true)

这笔交易把 CSV 时间锁和 P2PKH 签名检查合进同一段赎回脚本——继承和托管条件用的就是这个形态。

### CSV 脚本构造

时间锁是一段简单的线性脚本，没有分支：

```python
from bitcoinutils.setup import setup
from bitcoinutils.transactions import Sequence
from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK

def create_csv_script():
    setup('testnet')
    
    # 3-block relative time lock
    relative_blocks = 3
    seq = Sequence(TYPE_RELATIVE_TIMELOCK, relative_blocks)
    
    # Combined CSV + P2PKH script
    redeem_script = Script([
        seq.for_script(),           # Push 3
        'OP_CHECKSEQUENCEVERIFY',   # Verify time lock
        'OP_DROP',                  # Remove delay value
        'OP_DUP',                   # Standard P2PKH starts here
        'OP_HASH160',
        p2pkh_addr.to_hash160(),
        'OP_EQUALVERIFY', 
        'OP_CHECKSIG'
    ])
    
    return redeem_script
```

### bitcoinutils CSV 函数

**`Sequence(TYPE_RELATIVE_TIMELOCK, blocks)`**：创建一个基于区块的相对延迟 sequence 对象。这个 sequence 值编码了将由 OP_CHECKSEQUENCEVERIFY 强制的时间约束。

**`seq.for_script()`**：返回供脚本操作码使用的 sequence 值（把延迟值压入栈）。

**`seq.for_input_sequence()`**：返回供交易输入 sequence 字段使用的值，CSV 会拿它来校验。

### 花费时间锁 UTXO

```python
def spend_csv_script():
    # Must wait 3 blocks after UTXO creation
    seq = Sequence(TYPE_RELATIVE_TIMELOCK, 3)
    
    # Set sequence in transaction input
    txin = TxInput(utxo_txid, utxo_vout, sequence=seq.for_input_sequence())
    
    # Provide signature and redeem script
    sig = private_key.sign_input(tx, 0, redeem_script)
    txin.script_sig = Script([
        sig,                        # Signature for P2PKH
        public_key.to_hex(),        # Public key for P2PKH  
        redeem_script.to_hex()      # Reveal the script
    ])
```

### CSV 栈执行分析

我们用 testnet 例子里的真实交易数据把执行走一遍：

**ScriptSig 数据**：
- Signature：`30440220...`（71 字节）
- Public Key：`0250be5f...6bb4d3`（33 字节）
- Redeem Script：`53b27576a9145cdc...88ac`（28 字节）

## 阶段 1：P2SH 哈希验证

**（栈重置机制同样适用——细节见多签那一节）**

## 阶段 2：CSV + P2PKH 执行

**初始状态**（P2SH 重置之后）：

```
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

### 1. PUSH 3：时间延迟要求

```
│ 3 (delay_blocks)                       │
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

### 2. OP_CHECKSEQUENCEVERIFY：验证时间锁
CSV 校验交易输入的 sequence number >= 3：

```
│ 3 (delay_blocks)                       │
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

**（验证：自 UTXO 创建以来 nSequence >= 3 个区块）**

### 3. OP_DROP：移除延迟值

```
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

### 4. OP_DUP：开始 P2PKH 验证

```
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

### 5. OP_HASH160：哈希公钥

```
│ 5cdc28d6b1876...cabaadcc (pubkey_hash) │
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

### 6. PUSH 期望哈希：来自赎回脚本

```
│ 5cdc28d6b1876...cabaadcc (expected_hash) │
│ 5cdc28d6b1876...cabaadcc (computed_hash) │
│ 0250be5fc44ec...4d3 (pubkey)             │
│ 30440220a1b2...c3d401 (signature)        │
└──────────────────────────────────────────┘
```

### 7. OP_EQUALVERIFY：确认哈希匹配

```
│ 0250be5fc44ec...4d3 (pubkey)           │
│ 30440220a1b2...c3d401 (signature)      │
└────────────────────────────────────────┘
```

### 8. OP_CHECKSIG：最终签名验证

```
│ 1 (true)                               │
└────────────────────────────────────────┘
```

**（时间锁满足、签名验证通过——CSV 花费成功）**

### 时间锁错误处理

**常见错误：`non-BIP68-final`**

如果你在时间锁到期前就尝试花费：

```python
# This will fail if fewer than 3 blocks have passed
response = requests.post(mempool_api, data=signed_tx)
# Returns: "non-BIP68-final"
```

交易被拒，因为 `nSequence < required_delay`，违反了 CSV 约束。

### CSV 用在哪里

- **继承**：在所有者一段时间不活动后，资金对继承人变得可花费。
- **托管**：主条件未满足时，过了延迟就开放一条 fallback 路径。
- **支付通道**：Lightning 用 CSV 强制结算延迟，这正是给了每一方一个窗口去对旧状态提出异议。

## 3.4 P2SH 对比 P2PKH：P2SH 加了什么、又卡在哪

P2SH 把比特币脚本从单签授权扩展到多方和基于时间的条件，同时保持同样紧凑的地址格式。但它有一个局限，正是这个局限催生了 Taproot 接下来做的一切。

当一个 P2SH 输出被花费时，*整段*赎回脚本都会被揭示——每一条分支，无论它有没有被走到。没有办法只暴露相关的那一条。于是结构是线性、完全可见的：每一条签名路径、时间锁条款、fallback 条件，最后都上了链。而且因为赎回脚本要塞进 scriptSig，多签和继承这类设置会带来不小的体积开销，也就是更高的手续费。

Taproot 直接解决这两点：复杂脚本在需要之前一直藏着，承诺进一棵树里，只有实际执行的那条路径才会被揭示。这正是后面几章接住的线索。

## 本章小结

P2SH 把一段脚本锁在它的哈希后面，只在花费时揭示。我们搭起了后面全书反复出现的两个模式：

- **多签** —— `OP_CHECKMULTISIG` 配一个 2-of-3 赎回脚本，外加补它差一位 bug 的 `OP_0`。
- **时间锁** —— `OP_CHECKSEQUENCEVERIFY` 做一个相对延迟，配上一次 P2PKH 检查。

两者我们都在栈上走了一遍，包括 P2SH 的两阶段执行：先验证脚本的哈希，再重置栈、运行揭示出的脚本。

有一个局限对后文最关键：P2SH 在花费时揭示*整段*赎回脚本，每条分支都在内。Taproot 针对的正是这一点——只揭示你用的那条分支——而这是全书后面所要搭向的目标。

**下一章。** 第 4 章转到 SegWit：把见证移出交易主体，修掉可锻性，并为 Taproot 基于见证的花费路径做铺垫。
