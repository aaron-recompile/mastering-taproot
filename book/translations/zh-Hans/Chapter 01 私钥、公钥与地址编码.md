# 第 1 章：私钥、公钥与地址编码

每一笔 Bitcoin 花费，最终都回到同一条派生链：私钥（private key）生成公钥（public key），公钥生成地址（address）。本章把这条链从头走到尾——生成一个 key、编码、再变成本书后面会反复遇到的四种地址格式。这里的内容还不涉及 Taproot，但结尾引入的两样东西——x-only 公钥（x-only public key）和 Bech32m——正是 Taproot 的地基。

## 1.1 派生链

Bitcoin 的所有权模型是一条单向链。每一个箭头正向计算都很便宜，反向则不可行：

```text
Private Key (256-bit) -> Public Key (ECDSA point) -> Address (encoded hash)

```

三个部分分工清楚：私钥负责签名，公钥让任何人验证这个签名，地址是你对外公布、用来收款的那串短字符串——而公钥本身在你花费之前一直藏着。

## 1.2 私钥：所有权的根基

一个 Bitcoin 私钥就是一个 256-bit 的数——从 2^256 的空间里随机取出的整数。这个空间本身就是全部的安全论证：它的量级和可观测宇宙中原子的估计数量相当，所以"猜出别人的 key"不是任何人能采取的策略。

### 生成私钥

从 Python 的 `bitcoinlib` 开始：

```python
from bitcoinlib.keys import Key

# Generate a new Bitcoin key pair
key = Key()

# Extract the private key in different formats
private_key_hex = key.private_hex      # 32 bytes (256-bit) in hexadecimal
private_key_wif = key.wif()           # Wallet Import Format

print(f"Private Key (HEX): {private_key_hex}")
print(f"Private Key (WIF): {private_key_wif}")

```

**示例输出：**

```
Private Key (HEX): e9873d79c6d87dc0fb6a5778633389dfa5c32fa27f99b5199abf2f9848ee0289
Private Key (WIF): L1aW4aubDFB7yfras2S1mN3bqg9w3KmCPSM3Qh4rQG9E1e84n5Bd

```

hex 形式正好 64 个字符——256 bit、32 字节——这也是数学运算真正操作的对象。它同时很不留情：写错一个字符，你得到的是另一个看起来完全合法的 key，没有任何报错。WIF 就是用来堵这个缺口的。

### WIF（Wallet Import Format）

WIF 把原始 key 用 Base58Check 包了一层。这层包装加入了校验和（checksum），让笔误在造成损失前就被发现；去掉了视觉上容易混淆的字符（`0`、`O`、`I`、`l`）；并给每个钱包提供了一个统一的导入、导出字符串。

编码分四步：

1. **加版本前缀**：mainnet 用 `0x80`，testnet 用 `0xEF`。
2. **（可选）加压缩标志**：如果对应的公钥将以压缩形式使用，在负载末尾追加 `0x01`。正是这一个字节改变了 WIF 最终的 Base58 前缀。
3. **算校验和**：取 `SHA256(SHA256(data))`，保留前 4 字节。
4. **Base58 编码**，得到人类可读的字符串。

![WIF encoding flow](../../manuscript/resources/wif-encoding-flow.png)


图 1-1：WIF 编码把 32 字节私钥变成一个 Base58Check 编码的字符串

前缀一眼就能告诉你手里拿的是什么：

- **L** 或 **K**：mainnet 私钥（压缩）
- **c**：testnet 私钥

## 1.3 公钥：密码学上的验证点

公钥是 secp256k1 椭圆曲线上的一个点，由私钥乘以曲线固定的基点（base point）得到。这一步之所以不可逆，靠的就是乘法背后的运算；而在代码里，它只是一次属性读取。

### ECDSA 与 secp256k1

Bitcoin 用 ECDSA 在 secp256k1 曲线上签名，曲线方程为：

```
y² = x³ + 7

```

![Secp256k1 curve](../../manuscript/resources/Secp256k1.png)

图 1-2：Bitcoin 使用的 secp256k1 椭圆曲线

对本书要讲的一切，两条性质就够了：每个私钥 `k` 恰好映射到曲线上的一个点 `(x, y)`，而这个映射无法反向求解。

### 压缩公钥与非压缩公钥

公钥有两种写法。

**非压缩（65 字节）：**

```
04 + x-coordinate (32 bytes) + y-coordinate (32 bytes)

```

**压缩（33 字节）：**

```
02/03 + x-coordinate (32 bytes)

```

压缩之所以可行，是因为曲线方程允许你仅凭 `x` 还原出 `y`——只要知道 `y` 是偶是奇，而这一个 bit 就藏在前缀里：

- `02`：y 为偶
- `03`：y 为奇

```python
# Generate public keys in both formats
public_key_compressed = key.public_hex          # 33 bytes
public_key_uncompressed = key.public_uncompressed_hex  # 65 bytes

print(f"Compressed:   {public_key_compressed}")
print(f"Uncompressed: {public_key_uncompressed}") 

```

**示例输出：**

```
Compressed:   0250be5f...d126bb4d3
Uncompressed: 0450be5f...03162a90

```

现代实现一律使用压缩形式：字节减半，安全性不变。

### x-only 公钥：Taproot 的创新

Taproot 干脆去掉前缀，直接用 **x-only 公钥**——只保留 32 字节的 x 坐标。表示奇偶的那个字节消失了，因为 Taproot 固定了约定（key 一律取 `y` 为偶），这样每个 key 省下一字节，也让 Schnorr 的 key aggregation 保持干净。从第 5 章起，登场的就是这种格式。

```python
# Taproot uses x-only public keys (32 bytes)
taproot_pubkey = key.public_hex[2:]  # Remove the 02/03 prefix
print(f"X-only Public Key: {taproot_pubkey}")

```

## 1.4 地址生成：从公钥到收款目标

Bitcoin 地址**不是**公钥。它是公钥的一个编码后的哈希，而这多出来的一步哈希，一次买到三样东西：

- **隐私**：公钥在你花费之前一直隐藏。
- **对曲线被攻破的对冲**：椭圆曲线 key 前面挡着一层哈希，所以即便 secp256k1 将来出现弱点，也不会立刻暴露未花费的资金。
- **错误检测**：编码自带校验和。

### 地址生成流程

每一种 Bitcoin 地址的构造方式相同：

1. **哈希公钥**：先 SHA256，再 RIPEMD160（合起来即 Hash160）。
2. **加元数据**：版本字节与脚本类型信息。
3. **加校验和**：用于错误检测的字节。
4. **编码**：Base58Check 或 Bech32 / Bech32m。

![Legacy bitcoin address flow](../../manuscript/resources/Bitcoin_address_legacy.png)

图 1-3：以 Legacy 方式，通过哈希与编码把公钥转换成 Bitcoin 地址

```python
# Generate different address types from the same key
legacy_address = key.address()                          # P2PKH
segwit_native = key.address(encoding='bech32')          # P2WPKH
segwit_p2sh = key.address(encoding='base58', script_type='p2sh')  # P2SH-P2WPKH
taproot_address = key.address(script_type='p2tr')       # P2TR

print(f"Legacy (P2PKH):     {legacy_address}")
print(f"SegWit Native:      {segwit_native}")
print(f"SegWit P2SH:        {segwit_p2sh}")
print(f"Taproot:            {taproot_address}")

```

**示例输出：**

```
Legacy (P2PKH):     1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
SegWit Native:      bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kygt080
SegWit P2SH:        3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy
Taproot:            bc1plz0h3rlj2zvn88pgywqtr9k3df3p75p3ltuxh0

```

## 1.5 地址类型与编码格式

### Base58Check 编码

Base58Check 用于 legacy 地址，去掉视觉相近的字符，并嵌入校验和。

**排除的字符：** `0`（零）、`O`（大写 o）、`I`（大写 i）、`l`（小写 L）

**P2PKH（Pay-to-Public-Key-Hash）：**

- 前缀：`1`
- 格式：Base58Check 编码
- 用途：最初的 Bitcoin 地址格式
- 示例：`1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa`

**P2SH（Pay-to-Script-Hash）：**

- 前缀：`3`
- 格式：Base58Check 编码
- 用途：多签与封装的 SegWit 地址
- 示例：`3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy`

### Bech32 编码：SegWit 的创新

Bech32 随 SegWit 引入，不仅能检测常见笔误，往往还能指出错在哪个字符。

**P2WPKH（Pay-to-Witness-Public-Key-Hash）：**

- 前缀：`bc1q`
- 格式：Bech32 编码
- 优点：更低手续费，更强的错误检测
- 示例：`bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kygt080`

### Bech32m 编码：Taproot 的改进

Taproot 地址使用 Bech32m——对 Bech32 做了微调，修掉了原校验和的一个边界情况。

**P2TR（Pay-to-Taproot）：**

- 前缀：`bc1p`
- 格式：Bech32m 编码
- 优点：key path 与 script path 花费共用同一种地址格式
- 示例：`bc1plz0h3rlj2zvn88pgywqtr9k3df3p75p3ltuxh0`

## 1.6 地址格式对比

| 地址类型 | 编码 | 数据大小 | 地址长度 | 前缀 | 主要用途 |
| --- | --- | --- | --- | --- | --- |
| **P2PKH** | Base58Check | 25 字节 | ~34 字符 | `1...` | Legacy 支付 |
| **P2SH** | Base58Check | 25 字节 | ~34 字符 | `3...` | 多签、封装 SegWit |
| **P2WPKH** | Bech32 | 21 字节 | 42-46 字符 | `bc1q...` | SegWit 支付 |
| **P2TR** | Bech32m | 33 字节 | 58-62 字符 | `bc1p...` | Taproot 支付 |

地址编码有不少琐碎规则——版本字节、校验和、三套不同方案——但底下的想法比规则简单得多：

地址是给人看的。它是锁定脚本（scriptPubKey）的一个便于阅读的替身，并不是协议本身的一部分。一旦你认出前缀（`1`、`3`、`bc1q`、`bc1p`），你就已经知道背后是哪种脚本。从节点的角度看，Bitcoin 从不存储地址——只存储脚本。

后面的章节会一直盯着那个脚本——每种地址背后真正的 scriptPubKey。真正的逻辑在那里，Bitcoin 的可编程性也从那里开始。只要你能预测地址背后的脚本，你就能推理它如何被花费。

## 1.7 派生模型

一张图就能把整条链串起来——从生成 key，一直到真正落到链上的脚本。钱包用户永远只看到地址；作为开发者，你需要看清整条路径，因为节点强制执行的正是这条路径。

![Key-pubkey-address relationships](../../manuscript/resources/TheDerivationModel.png)

图 1-4：私钥、公钥、地址与 WIF 格式之间的派生关系

```
Private Key (k)
    ↓ ECDSA multiplication
Public Key (x, y)
    ↓ SHA256 + RIPEMD160
Public Key Hash (20 bytes)
    ↓ Version + Checksum + Encoding
Address (Base58/Bech32)
  ↓ Decoded by wallet/node
ScriptPubKey (locking script on-chain)
```

这条链在设计上是非对称的：

- **正向**：每一步计算都便宜。
- **反向**：每一步在计算上都不可行。
- **抗碰撞**：两个不同公钥产生同一个地址，概率小到可以忽略。

## 1.8 哪些东西延续到 Taproot

本章有三样东西，会在 Taproot 一出现时立刻回来：**x-only 公钥**（第 5 章）、作为 P2TR 地址格式的 **Bech32m**，以及"地址永远只是锁定脚本的替身"这个观念。尤其要记住最后一点——从这里开始，有意思的问题从来不是"地址是什么"，而是"背后是什么脚本，它怎么被花费"。第 2 章就从引入 Bitcoin Script 本身开始回答这个问题。
