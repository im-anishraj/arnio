import gzip
import os
import tempfile

import arnio as ar


def test_read_csv_gz_parity():
    # Create a temporary uncompressed CSV
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", encoding="utf-8", delete=False
    ) as uncompressed:
        uncompressed.write("id,name,value\n")
        uncompressed.write("1,alice,10.5\n")
        uncompressed.write("2,bob,20.0\n")
        uncompressed.write("3,charlie,30.2\n")
        uncompressed_path = uncompressed.name

    # Create a compressed version of it
    compressed_path = uncompressed_path + ".gz"
    with open(uncompressed_path, "rb") as f_in:
        with gzip.open(compressed_path, "wb") as f_out:
            f_out.writelines(f_in)

    try:
        # 1. Test read_csv
        df_uncompressed = ar.read_csv(uncompressed_path)
        df_compressed = ar.read_csv(compressed_path)

        # Compare columns and rows
        assert df_uncompressed.columns == df_compressed.columns
        assert len(df_uncompressed) == len(df_compressed)
        for col in df_uncompressed.columns:
            assert list(df_uncompressed[col]) == list(df_compressed[col])

        # 2. Test read_csv_chunked
        chunks_uncompressed = list(ar.read_csv_chunked(uncompressed_path, chunksize=2))
        chunks_compressed = list(ar.read_csv_chunked(compressed_path, chunksize=2))

        assert len(chunks_uncompressed) == len(chunks_compressed)
        for chunk_un, chunk_comp in zip(chunks_uncompressed, chunks_compressed):
            assert len(chunk_un) == len(chunk_comp)
            for col in chunk_un.columns:
                assert list(chunk_un[col]) == list(chunk_comp[col])

        # 3. Test scan_csv
        # scan_csv might be in arnio
        if hasattr(ar, "scan_csv"):
            schema_uncompressed = ar.scan_csv(uncompressed_path)
            schema_compressed = ar.scan_csv(compressed_path)
            assert schema_uncompressed == schema_compressed

    finally:
        if os.path.exists(uncompressed_path):
            os.remove(uncompressed_path)
        if os.path.exists(compressed_path):
            os.remove(compressed_path)
