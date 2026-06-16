# 第十章：RGB 与 Tapret——承诺隐藏在脚本树内部

## RGB 是什么

RGB 是构建在比特币之上的智能合约协议。合约状态在链下维护，由参与方自行验证（客户端验证）；比特币的角色只有一个——通过 UTXO 的花费顺序，确保状态转换不可逆、不可双花。Taproot 充当承诺载体：每次状态转换时，RGB 将一个密码学承诺嵌入 Taproot 输出的脚本树内部，链上不留任何可读信息。

---

## 与 Ordinals 相反：链上什么都看不到

第九章的 Ordinals 把数据放入见证字段。虚拟机跳过它，索引器读取它。链上有字节、有结构、有可解码的内容。

RGB 做的恰恰相反：链上什么都看不见。

同样的 Taproot 交易，两个普通的 P2TR 输出。`getrawtransaction` 返回 `OP_1 + 32 字节`，与任何密钥路径花费无法区分。RGB 的状态承诺藏在脚本树内部。比特币共识不执行它，不解释它，不知道它的存在。验证完全在客户端完成。

这是第九章与第十章之间的分界线：一个把数据存上链，另一个存的是承诺。

---

## Tapret：深度 1 处的不可花费叶节点

RGB 支持两种承诺方案。Opret 将承诺放在 OP_RETURN 交易输出中——34 字节，链上可见（本章中 **MPC** 代表 **Multi-Protocol Commitments**，多协议承诺，与密码学领域共享同一缩写的多方计算无关）：

```
Opret（交易输出）：
  scriptPubKey: OP_RETURN OP_PUSHBYTES_32 <32 字节 MPC 承诺>
  value: 0 sats

```

Tapret 不同——承诺不放在输出中，而是放在 Taproot 脚本树的一个叶节点内：

```
Tapret 叶脚本（64 字节，叶版本 0xC0）：
  50 50 ... 50              ← 29 字节 OP_RESERVED（0x50）
  6A                        ← OP_RETURN
  21                        ← OP_PUSHBYTES_33
  <32 字节 MPC 承诺>
  <1 字节 nonce>

```

叶内的 OP_RETURN 在脚本执行时立即终止并失败，使其永远无法被花费。但这个叶节点不是交易输出——它存在于脚本树内部，从外部看不见。¹

**插入位置**（LNPBP-12 规范）：深度 1，按 BIP-341 词典序排在最右侧。深度 0 是 Merkle 根；深度 1 是根的直接子节点。已有脚本成为深度 1 的左兄弟节点，Tapret 作为右兄弟节点插入深度 1。

以单个已有脚本 Script_A 为例：

```
之前：                         之后：

      P                               P'   ← 不同的调整密钥
      |                               |
  merkle_root                    merkle_root'
      |                           /           \
   Script_A               Script_A         Tapret_Leaf
  （深度 0，唯一叶）        （深度 1）       （深度 1，最右）
                                        不可花费，含 MPC 承诺

```

Merkle 根改变，输出密钥随之改变，但链上外观仍是标准 P2TR 地址。RGB 客户端获取 txid，定位输出，按规范在深度 1 的最右侧找到 Tapret 叶，提取 MPC 承诺，验证状态转换。

`tapret1st` 这个名称来自 LNPBP-12：`tapret` 是承诺方案名称，`1st` 对应深度 1（从 0 开始计数，根为 0）。

---

## 封印：状态与 UTXO 的绑定

RGB 用封印（single-use seal）将状态与具体的 UTXO 绑定。一个封印指向某笔交易的某个输出（txid:vout），当这个 UTXO 被花费时，封印关闭，状态转换完成且不可撤销。新交易的输出上会打开新封印，承接下一个状态。封印的作用类似于"谁持有这个 UTXO，谁就持有这份状态"——比特币 UTXO 的不可双花性，直接转化为 RGB 状态的不可双花性。

---

## 链上示例：测试网转账交易

以下实验运行在比特币测试网上——Alice 向 Bob 转移 100 单位 RGB20 资产。

**转账交易**：[64a14551...35c20b6b](https://mempool.space/testnet/tx/64a1455125724ce79d4914d7af5e0226f465c7522b8dd6f048440b8935c20b6b?showDetails=true)

在 mempool.space 上：

- vout:0：`tb1pd057tgt4u38ur4znyszme79l...jq02w5v`，V1_P2TR
- vout:1：`tb1p9yjaffzhuh9p7d9gnwfunxssn...hqellhrw`，V1_P2TR

两个输出都是标准 P2TR。链上没有任何 RGB 痕迹。运行 `code/chapter10/02_verify_tx_onchain.py` 直接验证：

```bash
python3 02_verify_tx_onchain.py 64a1455125724ce79d4914d7af5e0226f465c7522b8dd6f048440b8935c20b6b

```

输出：

```
vout[0]  type=v1_p2tr  value=600 sats   tb1pd057...
vout[1]  type=v1_p2tr  value=2000 sats  tb1p9yja...

All outputs are P2TR. No OP_RETURN. Indistinguishable from a normal Taproot spend.

```

**转账后 Bob 的状态**（RGB 客户端输出）：

```
Owned:
  State         Seal                                                   Witness
  assetOwner:
          100   bc:tapret1st:64a14551...c20b6b:1   bc:64a14551...c20b6b
                                                   (bitcoin:4909164, 2026-04-04 03:49:34)

```

逐字段说明：


| 字段                     | 值         | 含义                      |
| ---------------------- | --------- | ----------------------- |
| `100`                  | 100       | Bob 当前资产余额              |
| `bc:tapret1st:`        | 前缀        | 承诺方案：比特币测试网，Tapret，深度 1 |
| `64a14551...c20b6b:1`  | txid:vout | 承诺锚定到该交易的 vout:1        |
| `bc:64a14551...c20b6b` | witness   | 链上锚点 txid               |
| `bitcoin:4909164`      | 区块高度      | 交易确认时的高度                |


封印 `tapret1st:64a14551...c20b6b:1` 指向 mempool 上可见的 vout:1——一个标准 P2TR 输出。脚本树内的 Tapret 叶不会出现在 mempool 上；它存在于 RGB 客户端的 consignment 数据中。

**封印生命周期**

创世封印（已关闭）：

```
22d13f86...5d2a:0  ->  1,000,000 单位  ->  已花费

```

本次转账在同一笔交易上打开两个新封印：

```
转账交易：64a14551...c20b6b
  vout:0  ->  tapret1st:...:0  ->  999,900（Alice 的找零）
  vout:1  ->  tapret1st:...:1  ->  100    （Bob 的收款）

守恒校验：999,900 + 100 = 1,000,000 [OK]

```

旧封印关闭；新交易在输出上打开两个新封印，每个对应一个脚本树内藏有 Tapret 承诺的 P2TR 输出。

---

## 代码：六步转账流程

本章实验依赖 RGB CLI 和 Esplora 索引器。环境搭建见 `code/chapter10/README.md`。以下是核心调用模式。

`01_rgb_transfer_single_hop.py` 将转账拆分为六个步骤，每步对应本章的一个阶段：

```python
def _rgb(wallet_dir: str, *args: str) -> str:
    """调用 rgb CLI 并返回 stdout。"""
    cmd = [rgb_bin, "-d", wallet_dir, "-n", network,
           *args, "--sync", f"--esplora={esplora}"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.stdout

```

每一步都通过这个包装函数调用 CLI。`--sync` 确保每次操作前钱包状态与链同步。

**转账后 Bob 的完整输出**：

```
Global:
  spec := ticker "TNW022", name "Testnet Workflow Asset", ...
  issuedSupply := 1000000

Owned:
  State         Seal                                                                            Witness
  assetOwner:
          100   bc:tapret1st:64a1455125724ce79d4914d7af5e0226f465c7522b8dd6f048440b8935c20b6b:1
                bc:64a1455125724ce79d4914d7af5e0226f465c7522b8dd6f048440b8935c20b6b
                (bitcoin:4909164, 2026-04-04 03:49:34)

```

**Alice 的完整状态（**`-a` **标志）**：

```
Owned:
  State         Seal                                                   Witness
  assetOwner:
       999900   bc:tapret1st:64a14551...c20b6b:0  ...  -- third-party
          100   bc:tapret1st:64a14551...c20b6b:1  ...  -- third-party
      1000000   bc:tapret1st:22d13f86...5d2a:0    ~    -- spent

```

`third-party` 不是错误。状态转换在协议层面有效，金额守恒，Bob 正确收到 100。`third-party` 是钱包描述符作用域问题：客户端可以看到这些封印存在，但无法将其识别为 Alice 当前可花费的状态。这是客户端视图层的属性，不是 RGB 协议问题。

---

## 比特币看到了什么，RGB 客户端看到了什么

```
链上（任何人可见）：
  tx 64a14551...c20b6b
  ├── vout:0  ->  P2TR 地址 tb1pd057...  （600 sats）
  └── vout:1  ->  P2TR 地址 tb1p9yja...  （2,000 sats）
  没有 OP_RETURN 输出。没有任何 RGB 标记。

RGB 客户端（需要 consignment 才能解析）：
  vout:0 脚本树，深度 1：Tapret 叶
    -> MPC 承诺 -> Alice 的找零，999,900 单位
  vout:1 脚本树，深度 1：Tapret 叶
    -> MPC 承诺 -> Bob 的收款，100 单位

```

比特币共识验证签名和交易格式。Tapret 叶位于脚本树内部，从不被执行，对共识没有任何影响。外部观察者无法将这笔交易与普通 Taproot 转账区分开来。

与第九章对比：


|      | Ordinals/BRC-20  | RGB/Tapret      |
| ---- | ---------------- | --------------- |
| 承诺位置 | 见证字段（reveal 后可见） | 脚本树叶节点（永不可见）    |
| 链上数据 | 有（见证中含 JSON）     | 无               |
| 验证方  | 链下索引器            | RGB 客户端，客户端自行验证 |
| 信任模型 | 依赖索引器共识          | 客户端独立验证         |


---

## Tapret 如何改变输出密钥

将 Tapret 叶插入脚本树会改变 Merkle 根，直接影响第五章的公式：

```
t = HashTapTweak(internal_key || merkle_root)
Q = internal_key + t * G

```

输出密钥 `Q` 就是链上的 Taproot 地址。调整量 `t` 现在编码的是 RGB 状态承诺而非花费条件，但 `Q` 与任何其他 Taproot 密钥无法区分。没有办法判断一个调整量来自可花费的脚本树还是不可花费的 Tapret 叶。

`code/chapter10/03_tapret_leaf.py` 用纯 Python 构造这个 64 字节的叶，并逐字节打印结构——不需要 RGB CLI，任何人都可以运行。

**对钱包识别的影响：** 输出的持有者必须将调整量与 HD 派生路径一起存储。没有它，钱包无法从内部密钥重新计算 `Q`，也就无法识别该输出属于自己。在 RGB 钱包实现中，这些调整量以 HD 终端路径（例如 `&10/19`）为键存储在映射文件（`descriptor.toml`）中。如果这个映射丢失，输出会显示为 third-party——资金并未消失（私钥仍然存在），但钱包无法识别它们。

这是 Taproot 的通用属性，不是 RGB 特有的：任何向脚本树插入非标准叶的协议，都必须持久化调整量到密钥的映射，输出持有者才能维持花费能力。

---

## 本章小结

RGB 通过 Tapret 将状态承诺隐藏在 Taproot 脚本树深度 1 处。叶内的 OP_RETURN 在脚本执行时立即终止并失败，使其永远无法被花费；固定长度 64 字节，位置由 LNPBP-12 标准规定。链上输出是标准 P2TR 地址；Tapret 叶作为脚本树的一部分改变了 Merkle 根和输出密钥，但对外部观察者不可见。

封印是 RGB 状态与特定 UTXO 之间的绑定点。UTXO 被花费时旧封印关闭；新交易在输出上打开新封印——一个给找零，一个给接收方。金额守恒由 RGB 客户端从 consignment 数据中验证，不涉及任何索引器。

Tapret 利用了 Taproot 脚本树的 Merkle 承诺结构——没有脚本被执行，没有路径被花费。一个叶节点被插入树中，输出密钥悄无声息地携带着对任何外部观察者都不可见的状态锚点。RGB 没有引入新的交易格式，也没有改变任何共识规则；它依赖的是 BIP-341 中已有的属性：脚本树决定输出密钥。

下一章介绍闪电网络的 Taproot 通道：同样是 Taproot 输出，但承诺结构和更新机制完全不同——通道状态以对称方式保存在链下，只有在争议发生时才会浮现到链上。

---

¹ 本章的 Tapret 叶结构遵循当前 RGB 实现（rgb-wallet 0.11.0-beta.9），已通过测试网 PSBT 输出验证，与 [RGB 文档：Tapret](https://docs.rgb.info/commitment-layer/deterministic-bitcoin-commitments-dbc/tapret) 一致。LNPBP-12 原始草案描述了略有不同的字节布局；两者都产生 64 字节的不可花费叶。如果你使用的是不同版本的 RGB，请解码自己的 PSBT 输出来验证实际结构——详情及对比见 `code/chapter10/README.md`。