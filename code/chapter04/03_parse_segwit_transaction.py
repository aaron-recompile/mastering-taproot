"""
Real SegWit Transaction Parsing - Using Actual On-Chain Data

This script demonstrates how to parse a SegWit transaction hex string
and extract all components using real on-chain transaction data.

Reference: Chapter 4, Sections 4.2 and 4.3

✅ VERIFIED: This code uses real testnet transaction data.
   Real transaction TXID: 271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6
   View on explorer: https://blockstream.info/testnet/tx/271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6
"""

import struct
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey, P2wpkhAddress
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.utils import to_satoshis
from bitcoinutils.script import Script


def parse_varint(data, offset):
    """Parse variable-length integer from transaction data"""
    first_byte = data[offset]
    if first_byte < 0xfd:
        return first_byte, offset + 1
    elif first_byte == 0xfd:
        return struct.unpack('<H', data[offset+1:offset+3])[0], offset + 3
    elif first_byte == 0xfe:
        return struct.unpack('<I', data[offset+1:offset+5])[0], offset + 5
    else:  # 0xff
        return struct.unpack('<Q', data[offset+1:offset+9])[0], offset + 9


def parse_segwit_transaction(tx_hex):
    """Parse a SegWit transaction hex string into components"""
    tx_bytes = bytes.fromhex(tx_hex)
    offset = 0
    
    # Version (4 bytes, little-endian)
    version = struct.unpack('<I', tx_bytes[offset:offset+4])[0]
    offset += 4
    
    # Check for SegWit marker and flag
    is_segwit = False
    if offset < len(tx_bytes) and tx_bytes[offset] == 0x00:
        marker = tx_bytes[offset]
        offset += 1
        flag = tx_bytes[offset]
        offset += 1
        is_segwit = True
    else:
        marker = None
        flag = None
    
    # Input count
    input_count, offset = parse_varint(tx_bytes, offset)
    
    inputs = []
    for i in range(input_count):
        # TXID (32 bytes, little-endian, but displayed as big-endian)
        if offset + 32 > len(tx_bytes):
            break
        txid_bytes = tx_bytes[offset:offset+32]
        txid = txid_bytes[::-1].hex()  # Reverse for display (little-endian to big-endian)
        offset += 32
        
        # VOUT (4 bytes, little-endian)
        vout = struct.unpack('<I', tx_bytes[offset:offset+4])[0]
        offset += 4
        
        # ScriptSig length
        script_sig_len, offset = parse_varint(tx_bytes, offset)
        script_sig = tx_bytes[offset:offset+script_sig_len].hex() if script_sig_len > 0 else ''
        offset += script_sig_len
        
        # Sequence (4 bytes, little-endian)
        sequence = struct.unpack('<I', tx_bytes[offset:offset+4])[0]
        offset += 4
        
        inputs.append({
            'txid': txid,
            'vout': vout,
            'script_sig': script_sig,
            'script_sig_len': script_sig_len,
            'sequence': f'{sequence:08x}'
        })
    
    # Output count
    output_count, offset = parse_varint(tx_bytes, offset)
    
    outputs = []
    for i in range(output_count):
        # Check if we have enough bytes
        if offset + 8 > len(tx_bytes):
            break
        # Value (8 bytes, little-endian)
        value = struct.unpack('<Q', tx_bytes[offset:offset+8])[0]
        offset += 8
        
        # Script length
        if offset >= len(tx_bytes):
            break
        script_len, offset = parse_varint(tx_bytes, offset)
        if offset + script_len > len(tx_bytes):
            break
        script_pubkey = tx_bytes[offset:offset+script_len].hex()
        offset += script_len
        
        outputs.append({
            'value': value,
            'value_hex': f'{value:016x}',
            'script_len': script_len,
            'script_pubkey': script_pubkey
        })
    
    # Witness data (if SegWit)
    witnesses = []
    if is_segwit and offset < len(tx_bytes):
        for i in range(input_count):
            if offset >= len(tx_bytes):
                break
            witness_item_count, offset = parse_varint(tx_bytes, offset)
            witness_items = []
            for j in range(witness_item_count):
                if offset >= len(tx_bytes):
                    break
                item_len, offset = parse_varint(tx_bytes, offset)
                if offset + item_len > len(tx_bytes):
                    break
                item_data = tx_bytes[offset:offset+item_len].hex() if item_len > 0 else ''
                offset += item_len
                witness_items.append({
                    'len': item_len,
                    'data': item_data
                })
            witnesses.append(witness_items)
    
    # Locktime (4 bytes, little-endian)
    locktime = 0
    if offset + 4 <= len(tx_bytes):
        locktime = struct.unpack('<I', tx_bytes[offset:offset+4])[0]
        offset += 4
    
    return {
        'version': f'{version:08x}',
        'is_segwit': is_segwit,
        'marker': f'{marker:02x}' if marker is not None else None,
        'flag': f'{flag:02x}' if flag is not None else None,
        'input_count': input_count,
        'inputs': inputs,
        'output_count': output_count,
        'outputs': outputs,
        'witnesses': witnesses,
        'locktime': f'{locktime:08x}',
        'total_size': len(tx_bytes)
    }


def compare_hardcoded_vs_actual():
    """Compare hardcoded transaction structure with actual parsed transaction"""
    setup('testnet')
    
    print("=" * 70)
    print("REAL SEGWIT TRANSACTION PARSING")
    print("=" * 70)
    
    # Use the REAL transaction from 02_create_segwit_transaction.py
    # This is the actual transaction that was broadcast to testnet
    private_key = PrivateKey('cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT')
    public_key = private_key.get_public_key()
    from_address = public_key.get_segwit_address()
    to_address = P2wpkhAddress('tb1qckeg66a6jx3xjw5mrpmte5ujjv3cjrajtvm9r4')
    
    # Real UTXO from testnet
    utxo_txid = '1454438e6f417d710333fbab118058e2972127bdd790134ab74937fa9dddbc48'
    utxo_vout = 0
    utxo_amount = 1000  # sats
    
    txin = TxInput(utxo_txid, utxo_vout)
    txout = TxOutput(to_satoshis(0.00000666), to_address.to_script_pub_key())
    
    # CRITICAL: has_segwit=True required
    tx = Transaction([txin], [txout], has_segwit=True)
    
    print("\n" + "=" * 70)
    print("PHASE 1: UNSIGNED TRANSACTION")
    print("=" * 70)
    
    unsigned_tx = tx.serialize()
    parsed_unsigned = parse_segwit_transaction(unsigned_tx)
    
    print(f"\nGenerated Transaction Hex:")
    print(f"  {unsigned_tx}")
    print(f"\nActual Parsed Components:")
    print(f"  Version:      {parsed_unsigned['version']}")
    print(f"  Is SegWit:    {parsed_unsigned['is_segwit']}")
    if parsed_unsigned['is_segwit']:
        print(f"  Marker:       {parsed_unsigned['marker']}")
        print(f"  Flag:         {parsed_unsigned['flag']}")
    print(f"  Input Count:  {parsed_unsigned['input_count']:02x}")
    
    if parsed_unsigned['inputs']:
        inp = parsed_unsigned['inputs'][0]
        print(f"  TXID:         {inp['txid']}")
        print(f"  VOUT:         {inp['vout']:08x} ({inp['vout']})")
        print(f"  ScriptSig:    {inp['script_sig'] if inp['script_sig'] else '(empty)'} (len: {inp['script_sig_len']})")
        print(f"  Sequence:     {inp['sequence']}")
    
    print(f"  Output Count: {parsed_unsigned['output_count']:02x}")
    
    if parsed_unsigned['outputs']:
        out = parsed_unsigned['outputs'][0]
        print(f"  Value:        {out['value_hex']} ({out['value']} satoshis)")
        print(f"  Script Len:   {out['script_len']:02x} ({out['script_len']} bytes)")
        print(f"  ScriptPubKey: {out['script_pubkey']}")
    
    print(f"  Locktime:     {parsed_unsigned['locktime']}")
    print(f"  Total Size:   {parsed_unsigned['total_size']} bytes")
    
    print("\n" + "=" * 70)
    print("REAL TRANSACTION DATA")
    print("=" * 70)
    print("  ✅ This is the actual transaction structure from testnet")
    print(f"  Input UTXO:   {utxo_txid}:{utxo_vout}")
    print(f"  Input Amount: {utxo_amount} sats")
    print(f"  Output Amount: 666 sats")
    print(f"  Fee:          334 sats")
    
    print("\n" + "=" * 70)
    print("PHASE 2: SIGNED TRANSACTION WITH WITNESS")
    print("=" * 70)
    
    # CRITICAL: Use sign_segwit_input with script_code and input amount
    script_code = public_key.get_address().to_script_pub_key()
    signature = private_key.sign_segwit_input(
        tx,
        0,
        script_code,
        to_satoshis(utxo_amount / 100000000)
    )
    
    # Set empty scriptSig and add witness
    txin.script_sig = Script([])
    tx.witnesses.append(TxWitnessInput([signature, public_key.to_hex()]))
    
    signed_tx = tx.serialize()
    parsed_signed = parse_segwit_transaction(signed_tx)
    
    print(f"\nGenerated Transaction Hex:")
    print(f"  {signed_tx[:100]}...")
    print(f"\nActual Parsed Components:")
    print(f"  Version:      {parsed_signed['version']}")
    print(f"  Is SegWit:    {parsed_signed['is_segwit']}")
    if parsed_signed['is_segwit']:
        print(f"  Marker:       {parsed_signed['marker']}")
        print(f"  Flag:         {parsed_signed['flag']}")
    
    if parsed_signed['inputs']:
        inp = parsed_signed['inputs'][0]
        print(f"  TXID:         {inp['txid']}")
        print(f"  VOUT:         {inp['vout']:08x}")
        print(f"  ScriptSig:    {inp['script_sig'] if inp['script_sig'] else '(empty)'} (len: {inp['script_sig_len']})")
        print(f"  Sequence:     {inp['sequence']}")
    
    if parsed_signed['outputs']:
        out = parsed_signed['outputs'][0]
        print(f"  Value:        {out['value_hex']} ({out['value']} satoshis)")
        print(f"  Script Len:   {out['script_len']:02x} ({out['script_len']} bytes)")
        print(f"  ScriptPubKey: {out['script_pubkey']}")
    
    if parsed_signed['witnesses']:
        witness = parsed_signed['witnesses'][0]
        print(f"  Witness Items: {len(witness)}")
        for i, item in enumerate(witness):
            print(f"    [{i}] Length: {item['len']} bytes")
            print(f"    [{i}] Data:    {item['data'][:40]}...{item['data'][-20:] if len(item['data']) > 60 else item['data']}")
    
    print(f"  Locktime:     {parsed_signed['locktime']}")
    print(f"  Total Size:   {parsed_signed['total_size']} bytes")
    
    print("\n" + "=" * 70)
    print("REAL ON-CHAIN TRANSACTION")
    print("=" * 70)
    print("✅ This transaction was successfully broadcast to testnet")
    print(f"   TXID: 271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6")
    print(f"   Explorer: https://blockstream.info/testnet/tx/271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6")
    print(f"   Input: 1,000 sats (V0_P2WPKH)")
    print(f"   Output: 666 sats (V0_P2WPKH)")
    print(f"   Fee: 334 sats")
    print(f"   Status: Confirmed on testnet")
    print("\nThis parsing demonstrates:")
    print("  - How to parse SegWit transaction hex strings manually")
    print("  - Real transaction structure analysis")
    print("  - Witness data extraction from actual on-chain data")
    print("  - Byte-level encoding of SegWit transactions")
    
    # Also parse the actual on-chain transaction hex
    print("\n" + "=" * 70)
    print("PARSING ACTUAL ON-CHAIN TRANSACTION HEX")
    print("=" * 70)
    
    # Real signed transaction hex from blockchain
    real_signed_tx_hex = "0200000000010148bcdd9dfa3749b74a1390d7bd272197e2588011abfb3303717d416f8e4354140000000000fdffffff019a02000000000000160014c5b28d6bba91a2693a9b1876bcd3929323890fb202473044022015098d26918b46ab36b0d1b50ee502b33d5c5b5257c76bd6d00ccb31452c25ae0220256e82d4df10981f25f91e5273be39fced8fe164434616c94fa48f3549e33c03012102898711e6bf63f5cbe1b38c05e89d6c391c59e9f8f695da44bf3d20ca674c851900000000"
    parsed_real = parse_segwit_transaction(real_signed_tx_hex)
    
    print(f"\nOn-Chain Transaction Hex (first 100 chars):")
    print(f"  {real_signed_tx_hex[:100]}...")
    print(f"\nParsed Components from On-Chain Data:")
    print(f"  Version:      {parsed_real['version']}")
    print(f"  Is SegWit:    {parsed_real['is_segwit']}")
    if parsed_real['is_segwit']:
        print(f"  Marker:       {parsed_real['marker']}")
        print(f"  Flag:         {parsed_real['flag']}")
    print(f"  Input Count:  {parsed_real['input_count']}")
    if parsed_real['inputs']:
        inp = parsed_real['inputs'][0]
        print(f"  TXID:         {inp['txid']}")
        print(f"  VOUT:         {inp['vout']}")
        print(f"  ScriptSig:    {inp['script_sig'] if inp['script_sig'] else '(empty)'}")
    if parsed_real['outputs']:
        out = parsed_real['outputs'][0]
        print(f"  Value:        {out['value']} satoshis")
        print(f"  ScriptPubKey: {out['script_pubkey']}")
    if parsed_real['witnesses']:
        witness = parsed_real['witnesses'][0]
        print(f"  Witness Items: {len(witness)}")
        for i, item in enumerate(witness):
            print(f"    [{i}] Length: {item['len']} bytes")
            if item['len'] > 0:
                print(f"    [{i}] Data:    {item['data'][:40]}...{item['data'][-20:] if len(item['data']) > 60 else item['data']}")
    print(f"  Total Size:   {parsed_real['total_size']} bytes")


if __name__ == "__main__":
    compare_hardcoded_vs_actual()

