# 第九章：Ordinals 与 BRC-20 —— 单叶子脚本路径中的数据信封

## 一个用来承载数据的单叶子

Ordinals 与 BRC-20 在 2023 年曾引发大量关注，主网上也存在大量相关交易。若你观察其链上结构，会发现它们出奇地简单：**单叶子 Taproot 脚本路径、一笔承诺交易、一笔揭示交易**。

前八章从单叶子写到四叶子，脚本树越来越复杂。Ordinals 则退回**单叶子** —— 不是因为更简单，而是目的不同：叶子里的脚本**不是为了执行某种条件**，而是为了**承载数据**。虚拟机跳过数据段，数据留在 witness 里，由**链下索引器**读取。

我们可以用 Taproot 那几章里同一套 commit–reveal 机制把它拆开——只不过这里被揭示的叶子承载的是数据，而不是花费条件。

---

## 数据信封：`OP_0 OP_IF ... OP_ENDIF`

Ordinals 的叶子脚本形如：

```
<pubkey> OP_CHECKSIG
OP_0
OP_IF
  <"ord">
  OP_1
  <content-type>
  OP_0
  <data>
OP_ENDIF
```

虚拟机执行路径：

```
  <pubkey> OP_CHECKSIG  ← 验证签名，已执行
  OP_0                  ← false 入栈，已执行
  OP_IF                 ← 条件为假，跳转到 OP_ENDIF
  ┌──────────────────────────────────────┐
  │  "ord"                               │
  │  content-type                        │  ← 虚拟机跳过
  │  JSON payload                        │     索引器在此读取
  └──────────────────────────────────────┘
  OP_ENDIF              ← 恢复执行
```

虚拟机跳过的那些字节**仍在 witness 里**，随揭示交易上链承诺，之后不可更改。Bitcoin 共识验证签名与脚本格式；**不解释**数据内容。链下索引器可扫描 witness，按其协议规则计算代币状态（具体 JSON 格式见下文链上示例）。

BRC-20 使用**同一结构**，但对 JSON 字段（`p` / `op` / `tick` / `amt`）约定了写法。

---

## 链上示例：testnet BRC-20 铸造交易对

以下两笔 testnet 交易是本节分析的基础：

**承诺（Commit）**：[515ddcfc...1f950aa0](https://mempool.space/testnet/tx/515ddcfc2ddb5ebadb6be493a955e490c54d399cf2cc528cecc302e41f950aa0?showDetails=true)

| 字段 | 取值 |
|---|---|
| 输入 | 2,400 sats，key-path 地址 |
| 输出 0 | 1,046 sats -> `tb1pe7dahu72...seqqfsp`（临时地址） |
| 输出 1 | 1,054 sats -> 找零 |
| 手续费 | 300 sats |
| Witness | 单条 Schnorr 签名（key path） |

铭文内容通过 Taproot tweak **间接承诺**进输出公钥；链上看不到 JSON。

**揭示（Reveal）**：[2fc169a5...fff57547](https://mempool.space/testnet/tx/2fc169a5eb2f096bc8e64cb946380869ee2a2099f67cc3d5e719fbe9fff57547?showDetails=true)

| 字段 | 取值 |
|---|---|
| 输入 | 1,046 sats，来自临时地址 |
| 输出 | 546 sats -> 目标地址 |
| 手续费 | 500 sats |
| Witness | 签名、铭文脚本、control block |

揭示交易的三个 witness 元素：

```
签名（连续十六进制，为显示换行）：
894bf65e9593b1ce18071d44325add446b91e4638271318f1980d432e5de88f
b743fcf7c69a5a3e98ffe0306944ddc1e4ab38e4c525fb1e0846263183a6de375

脚本：
2050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3ac
0063036f726451
18746578742f706c61696e3b636861727365743d7574662d38
00
357b2270223a226272632d3230222c226f70223a226d696e74222c
227469636b223a2244454d4f222c22616d74223a2231303030227d
68

Control block：
c150be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3
```

**脚本逐字节解码：**

| 字节 | 十六进制 | 含义 |
|-------|-----|---------|
| 1 | `20` | OP_PUSHBYTES_32 |
| 2–33 | `50be5fc4...bb4d3` | x-only 公钥 |
| 34 | `ac` | OP_CHECKSIG |
| 35 | `00` | OP_0（条件为假） |
| 36 | `63` | OP_IF |
| 37 | `03` | OP_PUSHBYTES_3 |
| 38–40 | `6f7264` | `"ord"` |
| 41 | `51` | OP_PUSHNUM_1 |
| 42 | `18` | OP_PUSHBYTES_24 |
| 43–66 | `74657874...7574662d38` | `"text/plain;charset=utf-8"` |
| 67 | `00` | OP_0 |
| 68 | `35` | OP_PUSHBYTES_53 |
| 69–121 | `7b2270...227d` | `{"p":"brc-20","op":"mint","tick":"DEMO","amt":"1000"}` |
| 122 | `68` | OP_ENDIF |

**Control block**（33 字节）：

```
c1  50be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3
```

首字节 `0xc1`：奇偶位 = 1，leaf version = `0xc0`（Tapscript）。其余 32 字节为内部公钥。单叶子树不需要 Merkle 路径；control block 共 33 字节，结构与第七章单叶子 control block **相同**。

---

## 代码：构造铭文叶子与临时地址

```python
private_key = PrivateKey.from_wif("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
public_key = private_key.get_public_key()

MINT_JSON = {"p": "brc-20", "op": "mint", "tick": "DEMO", "amt": "1000"}
brc20_hex = json.dumps(MINT_JSON, separators=(',', ':')).encode('utf-8').hex()

inscription_script = Script([
    public_key.to_x_only_hex(),
    "OP_CHECKSIG",
    "OP_0",
    "OP_IF",
    "6f7264",                                             # "ord"
    "OP_1",
    "746578742f706c61696e3b636861727365743d7574662d38",  # "text/plain;charset=utf-8"
    "OP_0",
    brc20_hex,
    "OP_ENDIF"
])

temp_address = public_key.get_taproot_address([[inscription_script]])
print(temp_address.to_string())
# tb1pe7dahu72sdy64u449nw3k8u36gptxvccgyvmqn0t02t8pcceym5seqqfsp
```

`get_taproot_address([[inscription_script]])` 传入**单叶子**列表，调用方式与第七章一致。生成的地址可与承诺交易的输出 0 核对。

---

## 代码：承诺与揭示（关键片段）

可完整运行的脚本在 `code/chapter09/`。

**承诺** —— key path，witness 仅一条签名：

```python
sig = private_key.sign_taproot_input(
    commit_tx, 0,
    [key_path_address.to_script_pub_key()],
    [utxo_amount],
    script_path=False
)
commit_tx.witnesses.append(TxWitnessInput([sig]))
# commit txid: 515ddcfc...1f950aa0
```

**揭示** —— script path，witness 为三元素集合：

```python
sig = private_key.sign_taproot_input(
    reveal_tx, 0,
    [temp_address.to_script_pub_key()],
    [inscription_amount],
    script_path=True,
    tapleaf_script=inscription_script,
    tweak=False
)
control_block = ControlBlock(
    public_key,
    [[inscription_script]],
    0,
    is_odd=temp_address.is_odd()
)
reveal_tx.witnesses.append(TxWitnessInput([
    sig,
    inscription_script.to_hex(),
    control_block.to_hex()
]))
# reveal txid: 2fc169a5...fff57547
```

`sign_taproot_input` 的参数与第七章 script-path 签名一致。`ControlBlock` 接收单叶子列表与叶子索引 `0`。

---

## 索引器

这笔交易是合法的 Tapscript 花费：签名有效、脚本格式正确。索引器扫描揭示交易的 witness，定位 `OP_0 OP_IF ... OP_ENDIF` 段，抽出 JSON，再按协议规则计算状态 —— **全部在链下完成**。

不同索引器对同一段链上历史可能给出**不同解释**。实践中不同 ord 版本之间曾出现分歧，导致不同交易所对同一铸造操作报出不同余额。这类协议的「正确性」最终仍取决于对**某一索引器**的信任。

---

## 章末小结

大量 Ordinals 与 BRC-20 交易共享同一链上结构：单叶子 Taproot 脚本路径，叶子里用 `OP_0 OP_IF ... OP_ENDIF` 作**数据信封**，先承诺锁定，再揭示上链。虚拟机验证签名与脚本格式，跳过数据段；**数据含义**由链下索引器决定。

下一章讲 RGB：同样是 Taproot 输出与链下协议的组合，但用 **single-use seals（一次性密封）** 把协议的安全边界拉回到可验证的链上承诺 —— 与这里依赖索引器的信任模型**根本不同**。
