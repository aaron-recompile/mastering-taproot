# 第 2 章：Bitcoin Script 基础——堆栈操作与 P2PKH

第 1 章落在一个判断上：地址不过是锁定脚本（locking script）的一个替身。这一章讲的就是那个脚本。不过在脚本跑起来之前，得先弄清它到底锁住的是什么——所以我们从 UTXO 模型讲起，再引入 Bitcoin Script，把一笔真实的 P2PKH 花费在栈上一个操作码（opcode）一个操作码地走完。Taproot 后面做的一切，都建立在这套相同的执行模型上。

## 2.1 UTXO 模型：数字现金，不是数字银行

在看脚本之前，先把 Bitcoin 怎么持有价值说准。它不记账户余额，用的是 **UTXO（Unspent Transaction Output，未花费交易输出）** 模型——这套模型的行为更像实物现金，而不像银行账户。

### 现金 vs. 银行：一个心智模型

银行账户是一个会上下浮动的数字。现金是一把离散的钞票，你花钱的方式是递出整张钞票、再找回零钱。Bitcoin 走的是第二种。

**传统银行（账户模型）**：

- 账户显示一个余额：$500
- 花掉 $350 就直接从余额里扣
- 结果：账户余额变成 $150
- 不需要处理“找零”

**Bitcoin UTXO 模型（现金模型）**：

- 你没有一个“$500 余额”
- 你持有的是一张张具体的“钞票”：一张 $200 加三张 $100
- 要花 $350，你必须拿出价值 $400 的钞票（$200 + $100 + $100）
- 你会收到 $50 作为一张新“钞票”找零
- 结果：你现在有一张 $100 和一张 $50

这种现金式行为不是界面层的小花样——它就是 Bitcoin 设计与安全模型的根基。

### UTXO 模型实战

走一笔 Alice 付给 Bob 的款。

**初始状态**：

- Alice 拥有一个 10 BTC 的 UTXO
- Bob 没有任何 bitcoin

**Alice 给 Bob 转 7 BTC**：

1. **交易输入**：Alice 的 10 BTC UTXO（必须被整个消耗）
2. **交易输出**：
    - 7 BTC 给 Bob（新 UTXO）
    - 3 BTC 找零回 Alice（新 UTXO）
3. **结果**：原来的 10 BTC UTXO 被销毁，两个新 UTXO 被创建

每个 UTXO 用“创建它的交易 + 它在该交易输出列表中的位置”来命名——`transaction_id:output_index`：

- Bob 的 UTXO：`TX123:0`（7 BTC）
- Alice 的找零：`TX123:1`（3 BTC）

### UTXO 的关键性质

有几条性质直接从现金模型推出来，值得单列，因为全书后面都靠它们：

- **完整消耗**：UTXO 必须整个花掉——不存在部分花费。
- **原子创建**：一笔交易要么完全成功（所有输入被消耗、所有输出被创建），要么完全失败。
- **找零处理**：输入与输出金额之间的差额会成为交易手续费，除非显式作为找零返回。
- **并行处理**：因为每个 UTXO 只能被花一次，多笔交易可以并行验证，不需要复杂的状态管理。

## 2.2 Bitcoin Script 与 P2PKH 基础

### Bitcoin Script：可编程的花费条件

一个 UTXO 承载的不只是金额，还有一段**锁定脚本（locking script，ScriptPubKey）**，写明它在什么条件下才能被花。要花掉它，就得提供一段**解锁脚本（unlocking script，ScriptSig）**来满足这些条件。两者被放在一起检验，通过了，网络才把这次花费当作有效。

### 脚本结构

```
Unlocking Script (ScriptSig) + Locking Script (ScriptPubKey) -> Valid/Invalid

```

**锁定脚本（ScriptPubKey）**：

- 附在每个 UTXO 输出上
- 定义花费条件
- 例：“只有能为公钥 X 提供有效签名的人才能花”

**解锁脚本（ScriptSig）**：

- 在花费 UTXO 时提供
- 包含满足锁定脚本所需的数据
- 例：“这是我的签名和公钥”

验证时，节点把两段脚本拼起来，当作一个程序执行，只有最终结果为 TRUE 才接受这次花费。

### 基于栈的执行

Bitcoin Script 运行在一个栈（stack）上，和 Forth、PostScript 这类语言是同一套模型。每个操作都作用在一个后进先出（LIFO）的栈上：数据被压入栈，操作码把参数弹出、再把结果压回去。一个简短的算术例子就能展示整套机制。

初始栈：空
```
│ (empty)                               │
└───────────────────────────────────────┘

```


PUSH 3

```
│ 3                                     │
└───────────────────────────────────────┘

```


PUSH 5
```

│ 5                                     │
│ 3                                     │
└───────────────────────────────────────┘
```

ADD 操作
```

│ 8                                     │
└───────────────────────────────────────┘
```
ADD 这一步就是整套模式的缩影：弹出栈顶两个数（先 5，后 3），相加，把结果（8）压回去。没有别的东西在发生。正是这种可预测性，让这套模型能承载复杂的花费条件，而不至于变成安全隐患。

### P2PKH：基础脚本

Pay-to-Public-Key-Hash（P2PKH）是最基础的脚本类型，也是在 Taproot 把事情复杂化之前、学习栈模型最合适的地方。

**P2PKH 锁定脚本**

```
OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG

```

用一句话说：这个 UTXO 可以被任何人花费，只要他能拿出一把哈希值等于 `pubkey_hash` 的公钥，外加一个来自对应私钥的有效签名。

**P2PKH 解锁脚本**

```
<signature> <public_key>

```

花费者提供两样东西：一个证明自己掌握私钥的数字签名，以及公钥本身——脚本会把这把公钥哈希后，与已承诺的哈希做比对。

### 真实案例：Satoshi 转给 Hal Finney

Bitcoin 史上第一笔付款——Satoshi Nakamoto 转 10 BTC 给 Hal Finney——是天然的例子。

**交易 ID**：[`f4184fc5...831e9e16`](https://mempool.space/tx/f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16?showDetails=true)

**交易结构**：

- **输入**：Satoshi 的 coinbase UTXO（挖矿得到的 50 BTC）
- **输出**：
    - 10 BTC 给 Hal Finney
    - 40 BTC 找零回 Satoshi

有一点要说明：那笔 2009 年的交易用的是 P2PK（Pay-to-Public-Key），把公钥直接嵌进锁定脚本，并不是 P2PKH。P2PKH 紧随其后出现并成为常规做法，因为对公钥做哈希既在链上更省空间，又能让公钥在花费前一直隐藏。下面的走查仍以 Hal 作为花费者，但用 P2PKH 脚本，这样栈追踪对应的就是 Bitcoin 最终定型的那种形态。

### 逐步执行 P2PKH —— Hal Finney 案例

设想 Hal 之后去花一个被 P2PKH 锁定的 10 BTC，把脚本从头到尾走一遍。

**锁定脚本**（来自 UTXO）：

```
OP_DUP OP_HASH160 OP_PUSHBYTES_20 340cfcffe029e6935f4e4e5839a2ff5f29c7a571 OP_EQUALVERIFY OP_CHECKSIG

```

**解锁脚本**（由 Hal 提供）：

```
OP_PUSHBYTES_71 30440220576497b7e6f9b553c0aba0d8929432550e092db9c130aae37b84b545e7f4a36c022066cb982ed80608372c139d7bb9af335423d5280350fe3e06bd510e695480914f01

OP_PUSHBYTES_33 02898711e6bf63f5cbe1b38c05e89d6c391c59e9f8f695da44bf3d20ca674c8519

```

解锁脚本先运行，压入它的两个项；接着锁定脚本的操作码把它们消耗掉。下面每一步展示的，都是所标注操作执行完之后的栈。

1. **把签名压栈**：
```
    
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
```
    
2. **把公钥压栈**：
```
    
│ 02898711...8519 (public_key)          │
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
``` 
3. **OP_DUP**：复制栈顶项（公钥）：
```
    
│ 02898711...8519 (public_key)          │
│ 02898711...8519 (public_key)          │
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
```    
4. **OP_HASH160**：对栈顶项做哈希：
```
    
│ 340cfcff...7a571 (hash160_result)     │
│ 02898711...8519 (public_key)          │
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
``` 
5. **压入期望哈希**：来自锁定脚本：
```
    
│ 340cfcff...7a571 (expected_hash)      │
│ 340cfcff...7a571 (computed_hash)      │
│ 02898711...8519 (public_key)          │
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
```

6. **OP_EQUALVERIFY**：比较栈顶两项，相等则都移除：
```
    
│ 02898711...8519 (public_key)          │
│ 30440220...914f01 (signature)         │
└───────────────────────────────────────┘
（哈希不匹配则脚本失败）
```    
7. **OP_CHECKSIG**：用公钥和交易验证签名：
```

│ 1 (TRUE)                              │
└───────────────────────────────────────┘
``` 
8. **最终检查**：脚本成功，因为栈上唯一剩下的项是非零值。

### P2PKH 的安全性质

这套设计落出四条性质，每一条后面都有用：

公钥哈希挡在公钥本身前面，所以公钥在首次花费前一直隐藏——这层**原像抗性（pre-image resistance）**也给“将来 ECDSA 被攻破”留了一点余量。**OP_CHECKSIG** 用密码学把花费和私钥绑死：只有持有那把私钥的人才能造出通得过的签名。因为签名对交易的细节做了承诺，它同时充当**完整性（integrity）**校验——签名后再改动交易，签名就验不过了。又因为每个签名只绑定一笔特定交易，它无法被抽出来在别处**重放（replay）**。

## 2.3 实操：构建一笔 P2PKH 交易

### 在测试网上做一笔 Legacy 到 SegWit 的真实交易

把前面这些拼到一起看的最清楚的办法，是真造一笔交易。下面用一个 Legacy P2PKH 输入在测试网上支付一个 SegWit 输出；之后我们再把广播结果拆开，在栈上追踪它的脚本。

```python
from bitcoinutils.setup import setup
from bitcoinutils.utils import to_satoshis
from bitcoinutils.transactions import Transaction, TxInput, TxOutput
from bitcoinutils.keys import P2wpkhAddress, P2pkhAddress, PrivateKey
from bitcoinutils.script import Script

def main():
    # Setup testnet environment
    setup('testnet')

    # Sender information - Legacy P2PKH
    private_key = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
    public_key = private_key.get_public_key()
    from_address_str = "myYHJtG3cyoRseuTwvViGHgP2efAvZkYa4"
    from_address = P2pkhAddress(from_address_str)

    # Receiver - SegWit address
    to_address = P2wpkhAddress('tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4')

    print(f"Sender Legacy Address: {from_address_str}")
    print(f"Receiver SegWit Address: {to_address.to_string()}")

    # Create transaction input (referencing previous UTXO)
    txin = TxInput(
        '34b90a15d0a9ec9ff3d7bed2536533c73278a9559391cb8c9778b7e7141806f7',
        1  # vout index
    )

    # Calculate amounts
    total_input = 0.00029606  # Input amount in BTC
    amount_to_send = 0.00029400  # Amount to send
    fee = total_input - amount_to_send  # Transaction fee

    # Create transaction output
    txout = TxOutput(to_satoshis(amount_to_send), to_address.to_script_pub_key())

    # Create unsigned transaction
    tx = Transaction([txin], [txout])

    print(f"Unsigned transaction: {tx.serialize()}")

    # Get the P2PKH locking script for signing
    p2pkh_script = from_address.to_script_pub_key()

    # Sign the transaction input
    signature = private_key.sign_input(tx, 0, p2pkh_script)

    # Create the unlocking script: <signature> <public_key>
    txin.script_sig = Script([signature, public_key.to_hex()])

    # Get the signed transaction
    signed_tx = tx.serialize()

    print(f"Signed transaction: {signed_tx}")
    print(f"Transaction size: {tx.get_size()} bytes")

if __name__ == "__main__":
    main()

```

### 关键函数与组件说明

这段脚本依赖三组 `bitcoinutils` 调用。先是 setup 与密钥：`setup('testnet')` 把库指向测试网，`PrivateKey()` 从 WIF 载入密钥，`P2pkhAddress()` / `P2wpkhAddress()` 分别为 Legacy 发送方和 SegWit 接收方构造地址对象。接着是构造：`TxInput()` 用 txid 加输出索引引用被花的 UTXO，`TxOutput()` 设定目的地与金额，`Transaction()` 把它们装配起来，`to_satoshis()` 把 BTC 换算成 satoshi（1 BTC = 100,000,000 satoshi）。最后是脚本与签名：`to_script_pub_key()` 从地址推出锁定脚本，`sign_input()` 对一个输入签名，`Script()` 把签名和公钥打包成解锁脚本。

### 真实数据分析与栈执行

运行这段代码会产出一笔被广播到测试网的真实交易。我们可以把它的字节重新拆开，确认脚本所做的，正是追踪所预测的。

**交易 ID**：[`bf41b474...a8e58355`](https://mempool.space/testnet/tx/bf41b47481a9d1c99af0b62bb36bc864182312f39a3e1e06c8f6304ba8e58355?showDetails=true)

**原始交易数据**：

```text
0200000001f7061814e7b778978ccb919355a97832c7336553d2bed7f39feca9
d0150ab934010000006a473044022055c309fe3f6099f4f881d0fd960923eb91af
f0d8ef3501a2fc04dce99aca609d0220174b9aec4fc22f6f81b637bbafec9554e4
97ec2d9f3ca4992ee4209dd047443d012102898711e6bf63f5cbe1b38c05e89d6c
391c59e9f8f695da44bf3d20ca674c8519ffffffff01d872000000000000160014
c5b28d6bba91a2693a9b1876bcd3929323890fb200000000
```

解锁脚本（ScriptSig）是承载花费证明的那部分。从原始字节里取出来：

```text
473044022055c309fe3f6099f4f881d0fd960923eb91aff0d8ef3501a2fc04dce
99aca609d0220174b9aec4fc22f6f81b637bbafec9554e497ec2d9f3ca4992ee4
209dd047443d012102898711e6bf63f5cbe1b38c05e89d6c391c59e9f8f695da44
bf3d20ca674c8519
```

**逐段解析**：

- `47`：OP_PUSHBYTES_71（压入 71 字节——签名）
- `304402...443d01`：DER 编码的签名（71 字节）
- `21`：OP_PUSHBYTES_33（压入 33 字节——公钥）
- `02898711...8519`：压缩公钥（33 字节）

被花的 UTXO 上的锁定脚本（ScriptPubKey）就是标准的 P2PKH 形态：

`76a914c5b28d6bba91a2693a9b1876bcd3929323890fb288ac`

**锁定脚本解析**：

- `76`：OP_DUP
- `a9`：OP_HASH160
- `14`：OP_PUSHBYTES_20（压入 20 字节）
- `c5b28d6bba91a2693a9b1876bcd3929323890fb2`：公钥哈希（20 字节）
- `88`：OP_EQUALVERIFY
- `ac`：OP_CHECKSIG

### 栈执行追踪

两段脚本都解析完，就可以对着真实数据一步步执行。

**初始状态**：

```
│ (empty)                               │
└───────────────────────────────────────┘
```
脚本：<signature> <pubkey> OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG

**第 1 步 - 压入签名**：

操作：PUSH 304402...443d01
```
│ 304402...443d01 (signature)           │
└───────────────────────────────────────┘
```
**第 2 步 - 压入公钥**：

操作：PUSH 02898711...8519
```
│ 02898711...8519 (public_key)          │
│ 304402...443d01 (signature)           │
└───────────────────────────────────────┘
```
**第 3 步 - OP_DUP**：

操作：复制栈顶项
```
│ 02898711...8519 (public_key)          │
│ 02898711...8519 (public_key)          │
│ 304402...443d01 (signature)           │
└───────────────────────────────────────┘
```
**第 4 步 - OP_HASH160**：

操作：Hash160(栈顶项)
计算：hash160(02898711...8519) = c5b28d6bba91a2693a9b1876bcd3929323890fb2
```
│ c5b28d6b...890fb2 (computed_hash)     │
│ 02898711...8519 (public_key)          │
│ 304402...443d01 (signature)           │
└───────────────────────────────────────┘
```
**第 5 步 - 压入期望哈希**：

操作：PUSH c5b28d6bba91a2693a9b1876bcd3929323890fb2
```
│ c5b28d6b...890fb2 (expected_hash)     │
│ c5b28d6b...890fb2 (computed_hash)     │
│ 02898711...8519 (public_key)          │
│ 304402...443d01 (signature)           │
└───────────────────────────────────────┘
```

**第 6 步 - OP_EQUALVERIFY**：

操作：比较栈顶两项，相等则都移除
验证：c5b28d6b... == c5b28d6b... [OK]（匹配）
```
│ 02898711...8519 (public_key)          │
│ 304402...443d01 (signature)           │
└───────────────────────────────────────┘
```
**第 7 步 - OP_CHECKSIG**：

操作：用公钥和交易验证签名
输入：

公钥：02898711...8519
签名：304402...443d01
交易数据：（用于签名的序列化交易）

验证：ECDSA 验证 [OK]（签名有效）
```
│ 1 (TRUE)                              │
└───────────────────────────────────────┘
```
**最终状态**：
```
│ 1 (TRUE)                              │
└───────────────────────────────────────┘
```
结果：成功（栈上为非零值）

### 交易广播结果

这笔交易被 Bitcoin 测试网接受，可以在这里查看：
[`mempool.space/testnet/tx/bf41b474...a8e58355`](https://mempool.space/testnet/tx/bf41b47481a9d1c99af0b62bb36bc864182312f39a3e1e06c8f6304ba8e58355?showDetails=true)

从结果里有几点值得读出来：

- 输入引用了交易 [`34b90a15...141806f7`](https://mempool.space/testnet/tx/34b90a15d0a9ec9ff3d7bed2536533c73278a9559391cb8c9778b7e7141806f7?showDetails=true) 索引 1 处的 UTXO。
- 输出把 29,400 satoshi 发到一个 SegWit 地址。
- 手续费是 206 satoshi（29,606 - 29,400）——输入减输出，正如 UTXO 模型所说。
- 签名证明了对私钥的掌握，却从没把私钥放上链。

### 这些会带进后面的章节

P2PKH 是 Bitcoin 可编程货币最小的一个完整例子：基于栈的执行、一个哈希承诺、一次签名检查。后面的一切都在复用这三块，只改动夹在它们之间的东西。P2SH（第 3 章）哈希的是整个**脚本**而非一把公钥，于是花费条件可以任意复杂，地址却依旧很短。P2WPKH（第 4 章）保留 P2PKH 的逻辑，但把签名挪进一个独立的见证（witness），从而修掉可锻性（malleability）。而 P2TR（第 5 章起）把同一套栈模型带进 Schnorr 签名和 Merkle 承诺的脚本树。操作码会变得更丰富，但这一页上的执行模型不变。

## 本章小结

这一章立起了后面每一章都默认成立的两件事。UTXO 模型把价值持有为一个个离散的输出、每个都整笔消耗，正是这一点让交易得以并行验证、不存在一个共享余额需要去锁。而 Bitcoin Script 给每个输出附上一段锁定脚本，由一段解锁脚本去满足，两者在同一个 LIFO 栈上一起检验。

- **栈上的 P2PKH** —— `OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG`：复制并哈希公钥，确认它与承诺的哈希匹配，再验证签名。
- **从构造到上链** —— 用 [`bitcoinutils`](https://github.com/karask/python-bitcoin-utils)，我们构造、签名并广播了一笔真实的测试网 P2PKH 花费，再把它的字节按同样的七步追溯回去。

**下一章。** 第 3 章转向 P2SH：它把整段脚本藏在一个哈希后面，只在花费时才揭示——这是迈向 Taproot 所建立的脚本树的第一步。
