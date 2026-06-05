# STYLE — Chinese Translation Style (for Mastering Taproot)
Version: v1.0 — locked

## 基本定位
本中文版本面向：**已经理解 Bitcoin 基本概念、但第一次认真阅读脚本与 Taproot 的工程型开发者**。

## 翻译原则
1. **不是直译，不是文学化中文**  
   ——目标是技术出版级，用“工程中文”。

2. **所有技术术语第一次出现必须保持英文（括号）**  
   例：
   - x-only 公钥（x-only public key）
   - 压缩公钥（compressed public key）
   - 控制块（control block）

3. 专有名词不翻  
   - Taproot / SegWit / Schnorr / PSBT / Merkle / Script / UTXO / key path / script path
   - OP_ / opcode 名称
   - secp256k1
   - Base58Check / Bech32 / Bech32m

4. 术语保持书内一致，不随章变化  
   举例：
   - locking script → 锁定脚本
   - spending condition → 花费条件
   - stack execution → 栈执行
   - tapleaf → TapLeaf（首字母 T）

5. 所有关键名词尽量 **短直**  
   不写“更加”“充分地”这种文学词  
   写：**直接、结构、验证、路径、执行、哈希**

6. 图/表标题格式统一：
图 x-y：xxxxx
表 x-y：xxxxx

7. 数学或流程描述保持 bullet list，不拼成长句  
——本书是 for 工程师，不是 for 新闻媒体。

## 一句话 summary
> 中文版不是翻译英文，是“把 Bitcoin Script 的外语技术内容变成中文工程语言”。