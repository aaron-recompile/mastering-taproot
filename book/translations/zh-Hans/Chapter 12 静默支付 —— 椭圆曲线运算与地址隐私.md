# 第十二章：静默支付——椭圆曲线运算与地址隐私

## 为什么本章重要

静默支付（BIP352）解决的是一个没有共识变更就能解决的问题：接收方公开一个静态地址，每笔支付产生一个全新的、不可关联的 Taproot 输出。链上看到的是普通 P2TR 转账。

数学核心是第五章密钥调整里的同一个公式 `P = Q + t·G`。调整量 `t` 从脚本树 Merkle 根换成了 ECDH 共享密钥。如果你理解了 Taproot 的调整机制，静默支付的数学就已经在你手里了。

---

## 地址复用问题

比特币地址一旦公开，所有支付到这个地址的交易在链上永久可见、相互关联。想象一个捐款页面，收款方公布了自己的接收地址，等于把完整的收款历史暴露给所有人。想用新地址，就得跟发送方提前沟通——公开收款场景根本做不到。

静默支付的做法是：接收方（Bob）发布一个包含两个公钥的静态地址（`B_scan` 和 `B_spend`）。发送方（Alice）用自己的输入私钥 `a` 与 `B_scan` 做 ECDH，得到共享密钥，对其哈希得到标量 `t`，推导出一次性公钥 `P = B_spend + t·G`，付款到这个地址。接收方用私钥 `b_scan` 对每笔交易的输入公钥做同样的 ECDH，重新推导 `P`，匹配则确认收款。双方没有任何交互，链上看到的是普通 P2TR 输出。

ECDH 的性质保证了这一点：`a · (b_scan · G) = b_scan · (a · G)`，其中 `a` 是 Alice 的输入私钥。Alice 用自己的私钥乘以 Bob 的公钥，Bob 用自己的私钥乘以 Alice 的公钥，结果相同——双方无需交换私钥，就能独立得出同一个共享密钥，进而算出同一个 `t`。

`b_scan` 的唯一作用是推导出调整因子 `t`。花费时 Bob 用的是 `b_spend + t`——椭圆曲线的线性性保证了标量加法对应点加法：`(b_spend + t)·G = B_spend + t·G = P`。

`t` 是双方都能独立算出的，但只有 Bob 持有 `b_spend`——所以只有 Bob 能构造出花费私钥 `b_spend + t`。Alice 付出去的钱，只有 Bob 能取。

静默支付把"交互"变成了密钥的预先发布。Bob 提前把 `B_scan` 公开，Alice 的支付交易又天然暴露了她的输入公钥——两个公钥在链上相遇，完成了一次无需任何通信的"交互"。

---

## 链上示例：测试网静默支付

以下实验在比特币测试网上运行，使用的是本书贯穿始终的 Alice 和 Bob 密钥。

**第一步：派生**（运行 `code/chapter12/01_silent_payment_derive.py`）

Bob 的静默支付密钥对：

```
B_scan:  0368a9712c41bafbfa25d3e86d317d97b389083100818da112088fedbb7c929e10
B_spend: 02a5b069dcbb0458bac6aa04a2000c63ad93bc4853b35512913cee0b8f7214bcce

```

Alice 与 Bob 的 ECDH 计算：

```
Alice 输入公钥（A，链上可见，Bob 扫描时读取）：
  0250be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3

Alice 用私钥 a 计算：a · B_scan -> ECDH 共享密钥
Bob  用私钥 b_scan 计算：b_scan · A -> 同一个共享密钥

ECDH 共享密钥：  039e285df17d85590910f9e115422f29cfd32be28271845cd1abba62e542a1abc9
调整量 t：       026a61d9053ee35bd74560c408fa3aeeee397291bad7cef0b2ce50f24ef55630
一次性公钥 P：   03963061c3a266ae856b7755f2203e6d57e2ac9b9abf43f9414c05474eebea6e8b

```

一次性 Taproot 地址：`tb1p9kq07ze6yu9lumrhgwrs9030nahrm7qq6cqjmz73a8ys9ya5rdvswnew3j`

Bob 用 `b_scan · A` 独立推导出同一个地址，匹配确认。

**第二步：发送**（运行 `code/chapter12/02_send_testnet.py`）

Alice 向这个一次性地址发送 5000 sats：

**发送交易**：[b93523c5...b0f778e8](https://mempool.space/testnet/tx/b93523c5784080f1ca402bca39edda109e6e64c0df576c964e64630fb0f778e8?showDetails=true)

在 mempool.space 上：

- 1 个输入（Alice 的 Taproot UTXO），2 个输出
- vout:0：`tb1p9kq07ze6yu9lumrhgwrs9030n...vswnew3j`，5000 sats，V1_P2TR
- vout:1：Alice 的找零，V1_P2TR

没有静默支付标记，没有 OP_RETURN，与任何 Taproot 转账无法区分。

**第三步：Bob 扫描并花费**（运行 `code/chapter12/03_bob_scan_and_spend.py`）

Bob 从交易中提取 Alice 的输入公钥，计算 `b_scan · A`，重新推导 P，匹配到 vout:0。然后计算花费私钥：

```
p = b_spend + t
p · G = (b_spend + t) · G = B_spend + t · G = P  [OK]

```

**花费交易**：[11774714...e1b8d91b](https://mempool.space/testnet/tx/11774714227d2c8c787372efff666dd0a27b044766e503a6241d28d2e1b8d91b?showDetails=true)

Bob 向自己的常规地址发送 4846 sats。链上：又一笔普通的 Taproot 转账，与 Bob 的静默支付地址没有任何关联。

---

## 数学：与 Taproot 调整相同的公式

静默支付的地址派生和 Taproot 的输出密钥派生是同一个结构：

```
Taproot（第五章）：
  output_key = internal_key + t · G
  t = HashTapTweak(internal_key || merkle_root)

静默支付（本章）：
  P = B_spend + t · G
  t = Hash("BIP0352/SharedSecret", shared_secret)

```

两者都利用了椭圆曲线的线性性：公钥上的点加法对应私钥上的标量加法。持有者始终可以通过将调整量加到私钥上来花费输出。

Alice 计算 `a · B_scan`，Bob 计算 `b_scan · A`，两者相等——这是 ECDH 的基本性质：`a · (b_scan · G) = b_scan · (a · G)`。无需任何通信，双方独立得出同一个共享密钥，再用它推导出同一个输出地址。

---

## 两密钥分离

Bob 发布的静态地址包含两个公钥 `B_scan` 和 `B_spend`，任何人可见。对应的两个私钥分工不同：`b_scan` 只能做 ECDH 推导出哪些输出属于 Bob，没有 `b_spend` 就无法花费——可以安全地委托给扫描服务器。`b_spend` 是构造花费私钥 `b_spend + t` 的唯一来源，必须严格保密。

---

## 本章小结

传统收款面临两难：固定地址便于公开，但暴露收款历史；换新地址需要交互沟通。静默支付绕开了这个两难——Bob 发布静态地址，Alice 的支付交易天然携带公钥，两者在链上完成一次没有通信的"交互"，每次推导出全新的一次性地址。

Bob 扫描属于自己的收款时对每笔交易的输入公钥做 ECDH，能推导出则收款归属确认，从而可以支取自己款项。

这是一种由数学保证的隐私：不需要中间人，不需要接收方配合——发送方单方面就能保护双方的隐私。

## Taproot 应用全景

至此，四个前沿章节全部完成——Taproot 在真实协议中的典型应用。每一个 Taproot 应用都在为其他所有应用扩大匿名集：静默支付输出、闪电通道关闭、Ordinals 铸造、RGB 状态转换，链上格式没有任何区别，全部是标准 P2TR。四章，四个协议，一种链上痕迹：


| 章节  | 应用       | Taproot 能力维度                      |
| --- | -------- | --------------------------------- |
| 9   | Ordinals | witness 存数据                       |
| 10  | RGB      | script path 藏承诺                   |
| 11  | 闪电网络     | key path（合作关闭）+ script path（合约结构） |
| 12  | 静默支付     | key path（公钥天然暴露）                  |


Taproot 仍在演进，还会有更多协议建立在同一套基础之上。学完本书，你已经有能力读懂它们。