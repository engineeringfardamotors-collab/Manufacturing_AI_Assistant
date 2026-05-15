import pandas as pd
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

from services.engine.mpn_reader import SapMpnReader

# --- Unit Test for MPN Reader ---
def test_sap_mpn_reader():
    mpn_file = 'data/uploads/EXPORT_MPN.xlsx'
    reader = SapMpnReader()

    print("=== UNIT TEST: SAP MPN READER ===")
    # Step 1: Read raw data
    df_raw = reader.read(mpn_file)
    assert not df_raw.empty, "DataFrame خوانده شده نباید خالی باشد"
    print(f"Raw DataFrame shape: {df_raw.shape}")
    print(f"Sample rows (first 5):\n{df_raw.head().to_string()}")

    # Step 2: Build lookup
    lookup = reader.build_lookup(df_raw)
    assert "mpn_to_internal" in lookup, "lookup باید شامل mpn_to_internal باشد"
    assert "internal_to_mpns" in lookup, "lookup باید شامل internal_to_mpns باشد"

    print("\n=== Lookup Structures ===")
    print(f"MPN to Internal count: {len(lookup['mpn_to_internal'])}")
    print(f"Internal to MPNs count: {len(lookup['internal_to_mpns'])}")

    # Sample checks
    sample_mpn = list(lookup['mpn_to_internal'].keys())[0]
    sample_internal = lookup['mpn_to_internal'][sample_mpn]
    print(f"Sample MPN mapping: '{sample_mpn}' -> '{sample_internal}'")

    reverse_sample = list(lookup['internal_to_mpns'].keys())[0]
    reverse_mpns = lookup['internal_to_mpns'][reverse_sample]
    print(f"Sample Internal mapping: '{reverse_sample}' -> {reverse_mpns}")

    return True

if __name__ == "__main__":
    try:
        test_result = test_sap_mpn_reader()
        if test_result:
            print("\n✅ All tests passed successfully.")
    except Exception as e:
        print(f"❌ Test failed: {e}")
