# 第十一章：闪电网络通道——从 P2WSH 多签到 Taproot 隐私通道

## 为什么本章重要

闪电网络是 Taproot 最初的设计动机之一。

第九章展示了 Taproot 的见证字段如何充当数据层（Ordinals）。第十章展示了 Taproot 的承诺能力如何锚定链下状态（RGB）。本章回到 Taproot 的核心设计目标：让复杂的多方合约在链上与普通支付无法区分。

闪电支付通道将资金锁入一个共同控制的输出，允许无限次链下余额更新，最终以单笔链上交易结算。在 Taproot 下，合作关闭——占全部通道关闭的 90% 以上——不留任何可将其与普通支付区分的痕迹。

---

## P2WSH：SegWit v0 脚本哈希

传统闪电通道建立在 P2WSH（Pay-to-Witness-Script-Hash）之上，它是 P2SH 的 SegWit v0 升级版。两者解决同一个问题：将复杂脚本的哈希放上链，只在花费时才揭示脚本本身。区别在于：P2SH 使用 HASH160（20 字节），P2WSH 使用 SHA256（32 字节），将抗碰撞性从 80 位提升到 128 位。P2WSH 还将脚本执行移入见证字段，享受 SegWit 的权重折扣。

传统闪电通道用 P2WSH 包装一个 2-of-2 多签：

```
见证脚本：
  OP_2 <alice_pubkey> <bob_pubkey> OP_2 OP_CHECKMULTISIG

ScriptPubKey（链上）：
  OP_0 <32 字节 SHA256(witness_script)>

```

资金输出只暴露一个哈希，但花费时见证字段会揭示一切：两个 DER 签名和完整的多签脚本。任何观察者都知道这是一个闪电通道。

---

## 链上示例：P2WSH 通道开启与关闭

使用本书贯穿始终的 Alice/Bob 密钥，将 10,000 sats 锁入 2-of-2 P2WSH：

```python
pubs = sorted([alice_pub.to_hex(), bob_pub.to_hex()])  # BIP67：词典序排序

witness_script = Script([
    'OP_2', pubs[0], pubs[1], 'OP_2', 'OP_CHECKMULTISIG'
])

p2wsh_addr = P2wshAddress.from_script(witness_script)

```

`sorted()` 调用确保无论两个公钥的传入顺序如何，生成的地址都相同——这是 BIP67 的要求，也是常见的实现陷阱。

输出：

```
Witness Script（十六进制）：52210250be5f...b27e2d77...210284b5...af552ae
Witness Script 大小：71 字节
资金地址（P2WSH）：tb1qztxpf2...393urj
ScriptPubKey：002012cc14a9...3afe3b71c
格式：OP_0 <32 字节 SHA256(witness_script)>

```

**资金交易**（双方签名并广播）：

[7c512abc...767a](https://mempool.space/testnet/tx/7c512abcdc86e48837e6e5ba57524c3ee25f1c4bd4bf7d42f7db084b2d09767a)

- vout:0：`tb1qztxpf2...393urj`，10,000 sats，P2WSH
- 观察者看到：`OP_0 <32 字节哈希>`——一个 SegWit v0 脚本哈希输出，几乎可以确定是多签

### 合作关闭

双方同意关闭通道，各自签名花费资金输出：

```python
alice_sig = alice_priv.sign_segwit_input(tx, 0, witness_script, fund_amount_sats)
bob_sig   = bob_priv.sign_segwit_input(tx, 0, witness_script, fund_amount_sats)

# P2WSH 见证：[空元素, alice_sig, bob_sig, witness_script]
tx.witnesses.append(TxWitnessInput([
    '',                      # OP_CHECKMULTISIG 历史遗留 bug 要求的空元素
    alice_sig,               # 71 字节，DER 编码
    bob_sig,                 # 71 字节，DER 编码
    witness_script.to_hex()  # 71 字节：脚本本身
]))

```

**合作关闭交易**：

[bd6da1cd...0461](https://mempool.space/testnet/tx/bd6da1cdd3740661875b2568c2b4494f818c3c3742f809e23512c43f52840461)

链上见证结构：

```
[0] 空元素        （OP_CHECKMULTISIG 历史遗留 bug）
[1] Alice 签名   （71 字节，DER 编码）
[2] Bob 签名     （71 字节，DER 编码）
[3] 见证脚本     （71 字节：OP_2 <pk_a> <pk_b> OP_2 OP_CHECKMULTISIG）

见证总计：约 214 字节

```

观察者的结论："这是 2-of-2 多签。几乎可以确定是闪电通道。"

---

## Taproot 通道：MuSig2 密钥聚合

Taproot 通道用纯密钥路径 Taproot 输出取代 P2WSH。2-of-2 多签通过 MuSig2（BIP 327）隐藏在单个聚合公钥内。外部观察者只看到一个 32 字节的仅含 x 坐标密钥——与任何单签名者 Taproot 地址无法区分。

### MuSig2 密钥聚合

简单地将公钥相加 `P_alice + P_bob` 有一个致命缺陷：Bob 可以声称自己的公钥是 `P_bob - P_alice`，使聚合结果等于 `P_bob` 本身——即**流氓密钥攻击**。

MuSig2 的解决方案是用一个系数对每个公钥加权，该系数从所有参与方密钥的完整集合中派生：

```
P_agg = H(L, P_alice) · P_alice + H(L, P_bob) · P_bob

其中 L = {P_alice, P_bob}（所有参与方密钥的集合）

```

Bob 无法伪造系数，因为系数依赖于他声明的公钥——改变密钥就改变系数，攻击因此失效。

在代码中，这由 BIP-327 参考实现的 `key_agg()` 处理：

```python
pk_alice = pubkey_to_plain(alice_pub)   # 33 字节压缩公钥
pk_bob   = pubkey_to_plain(bob_pub)

agg_ctx   = mu.key_agg([pk_alice, pk_bob])
xonly_agg = mu.get_xonly_pk(agg_ctx)

```

输出：

```
Alice 公钥：    0250be5fc4...26bb4d3
Bob 公钥：      0284b59516...63af5
聚合（x 坐标）：c9688c3935320a89911366a588bca56103ed295b3412a3061315a06d26d0069f

```

得到的 `c9688c...` 是聚合密钥的 x 坐标。任何一方都无法单独计算对应的私钥。

### BIP86 资金输出

聚合公钥还要再做一次 BIP86 调整。这样，通道双方都能确认：这个 funding output 只是一个 key-path-only 的 Taproot 输出，而不是表面看起来像单签、实际上还暗藏 script path：

```python
def bip86_tweak(xonly_agg: bytes) -> bytes:
    tag = b'TapTweak'
    tag_hash = hashlib.sha256(tag).digest()
    return hashlib.sha256(tag_hash + tag_hash + xonly_agg).digest()

tweak = bip86_tweak(xonly_agg)
agg_ctx_tweaked = mu.apply_tweak(agg_ctx, tweak, is_xonly=True)
xonly_output    = mu.get_xonly_pk(agg_ctx_tweaked)

```

输出：

```
BIP86 调整量：  29331a2bb167b04282e424a07120a614a9d6a68d48e4ae6567dfa34f29ea0e6c
输出密钥（x）：6ba767bc2cb48e003885e7e235ee942b5d1cbab2029e61db0f5d3cbd3f4d5bf8

```

最终地址：

```python
funding_pub  = PublicKey("02" + xonly_output.hex())
funding_addr = funding_pub.get_taproot_address()
# tb1pnn82l6...9m8uvc

```

**资金交易**（Alice 和 Bob 将 10,000 sats 锁入 MuSig2 聚合 + BIP86 输出）：

[b7efde1f...aace](https://mempool.space/testnet/tx/b7efde1f1659a6a48d998c7860d9a586ac65c6069e73ded9779f1f6e1898aace)

- vout:1：`tb1pnn82l6...9m8uvc`，10,000 sats，P2TR
- 观察者看到：`OP_1 <32 字节密钥>`——一个普通的 Taproot 地址。什么都有可能。

---

## MuSig2 合作关闭：四轮签名协议

关闭通道需要双方共同产生一个 Schnorr 签名。这是 BIP-327 的核心：任何一方都不需要看到对方的私钥，双方的贡献聚合成一个标准签名。

### 第一轮：NonceGen——各自生成随机 nonce

每个参与方独立生成一对秘密/公开 nonce：

```python
nonce_alice = mu.nonce_gen_internal(
    rand_=bytes(32),        # 随机字节（生产环境必须真正随机）
    sk=sk_alice,
    pk=pk_alice,
    aggpk=xonly_output,
    msg=msg,
    extra_in=None
)
nonce_bob = mu.nonce_gen_internal(
    rand_=bytes([1] * 32),
    sk=sk_bob,
    pk=pk_bob,
    aggpk=xonly_output,
    msg=msg,
    extra_in=None
)

pubnonce_alice = nonce_alice[1]   # 公开 nonce——可以交换
pubnonce_bob   = nonce_bob[1]
secnonce_alice = nonce_alice[0]   # 秘密 nonce——永远不要共享
secnonce_bob   = nonce_bob[0]

```

双方交换各自的公开 nonce。秘密 nonce 保持私密。

### 第二轮：NonceAgg——聚合公开 nonce

```python
aggnonce = mu.nonce_agg([pubnonce_alice, pubnonce_bob])

```

任何一方都可以执行这一步。得到的 `aggnonce` 是公开的。

### 第三轮：PartialSign——各自签名

这里有一个细微的工程细节：`bitcoinutils` 的 `get_taproot_address()` 在内部会自动应用一次 BIP86 调整。如果事先已手动应用过 BIP86 调整，链上输出密钥就被调整了两次。`SessionContext` 必须包含两次调整——只用一次调整构造的签名能通过本地 `schnorr_verify`，但会被比特币核心的内存池拒绝。这一点已在测试网上验证。

```python
# 第一次调整：手动应用于原始聚合密钥
agg_ctx_raw    = mu.key_agg(pubkeys)
xonly_raw      = mu.get_xonly_pk(agg_ctx_raw)
tweak1         = bip86_tweak(xonly_raw)

# 第二次调整：由 get_taproot_address() 在内部应用
agg_ctx_t1     = mu.apply_tweak(agg_ctx_raw, tweak1, is_xonly=True)
xonly_after_t1 = mu.get_xonly_pk(agg_ctx_t1)
tweak2         = bip86_tweak(xonly_after_t1)

# SessionContext 必须携带两次调整
session_ctx = mu.SessionContext(
    aggnonce, pubkeys,
    [tweak1, tweak2],   # 两次调整都需要
    [True, True],
    msg
)

psig_alice = mu.sign(secnonce_alice, sk_alice, session_ctx)
psig_bob   = mu.sign(secnonce_bob,   sk_bob,   session_ctx)

```

输出：

```
Alice 部分签名：3f8a1c2d...（只显示前 16 字节）
Bob 部分签名：  c12b9e4f...（只显示前 16 字节）

```

### 第四轮：SigAgg——聚合成最终签名

```python
final_sig = mu.partial_sig_agg([psig_alice, psig_bob], session_ctx)

assert mu.schnorr_verify(msg, xonly_output, final_sig)
# -> 验证：通过

```

输出：

```
聚合签名：    9e4f7a2b...（64 字节）
签名长度：    64 字节
验证结果：    通过（针对调整后的输出密钥）

```

Alice 从未看到 Bob 的私钥。Bob 从未看到 Alice 的私钥。两个部分签名聚合成一个——格式与任何单签名者的 Schnorr 签名完全相同。

### 广播合作关闭交易

```python
tx.witnesses.append(TxWitnessInput([final_sig.hex()]))

```

**MuSig2 合作关闭交易**：

[af6fdae8...9d1f](https://mempool.space/testnet/tx/af6fdae8c2731b2b83e74b8dd79bc2c241dea8aee8c8cfb6f094e44c13b39d1f)

链上见证结构：

```
[0] Schnorr 签名（64 字节）——由 Alice + Bob 的 MuSig2 聚合生成

见证总计：64 字节

```

观察者的结论："一笔普通的 Taproot 支付。没有任何异常。"

---

## 并排对比

同一个通道。同样的两个参与方。同样的最终余额分配。运行 `code/chapter11/03_compare_witness.py` 可以复现以下输出：

```
                          P2WSH              Taproot（MuSig2）
资金 scriptPubKey         OP_0 <32 字节>     OP_1 <32 字节>
资金观察者看到             "P2WSH，很可能      "Taproot 地址，
                           是多签"            可能是任何东西"

关闭见证元素数            4                  1
关闭签名数                2（DER，各约 71 字节）  1（Schnorr，64 字节）
关闭时暴露脚本             是（2-of-2）        否
关闭见证大小              214 字节           64 字节
关闭交易 vsize            168 vbytes         154 vbytes
可识别为通道               是                 否
见证节省                  ——                 70%

```

---

## 本章小结

闪电网络 Taproot 通道用 MuSig2 密钥聚合和 BIP86 纯密钥路径资金输出取代了 P2WSH 2-of-2 多签。合作关闭——最主要的通道关闭方式——产生一个 64 字节的 Schnorr 签名，与任何普通 Taproot 支付无法区分。P2WSH 暴露完整的多签脚本和两个独立的签名；Taproot 什么都不透露。

MuSig2（BIP 327）让两个参与方在互不知晓对方私钥的情况下共同控制一个公钥。四轮签名协议（NonceGen -> NonceAgg -> PartialSign -> SigAgg）在链上产生一个标准 64 字节 Schnorr 签名。BIP86 调整让通道双方都能确认：这个 funding output 是按 key-path-only 的方式构造出来的，而不是额外承诺了一棵隐藏脚本树。

P2WSH 让通道结构对任何观察者一目了然。Taproot 让它隐形。资金输出、合作关闭、见证字段——没有任何一项能将闪电通道与普通单密钥支付区分开来。