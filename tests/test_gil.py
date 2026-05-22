"""Tests to verify GIL is released around long C++ operations."""

import threading

import arnio as ar


def run_in_thread(fn, results, index):
    try:
        results[index] = fn()
    except Exception as e:
        results[index] = e


class TestGILReleaseCsvRead:
    def test_concurrent_csv_reads(self, tmp_path):
        """Multiple threads should be able to read CSVs concurrently."""
        path = tmp_path / "data.csv"
        lines = ["id,value"] + [f"{i},{i * 1.5}" for i in range(500)]
        path.write_text("\n".join(lines))

        results = [None, None]

        t1 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.read_csv(str(path)), results, 0)
        )
        t2 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.read_csv(str(path)), results, 1)
        )

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results[0].shape[0] == 500
        assert results[1].shape[0] == 500

    def test_concurrent_read_does_not_corrupt_data(self, tmp_path):
        """Concurrent reads should return correct data."""
        path = tmp_path / "data.csv"
        path.write_text("name,age\nAlice,30\nBob,25\nCharlie,35\n")

        results = [None, None, None]
        threads = [
            threading.Thread(
                target=run_in_thread, args=(lambda: ar.read_csv(str(path)), results, i)
            )
            for i in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for r in results:
            assert r.shape == (3, 2)


class TestGILReleaseCleaningOps:
    def test_concurrent_drop_nulls(self, tmp_path):
        """drop_nulls should run concurrently across threads."""
        path = tmp_path / "nulls.csv"
        path.write_text("name,age\nAlice,30\n,25\nCharlie,\nDiana,28\n")
        frame = ar.read_csv(str(path))

        results = [None, None]
        t1 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.drop_nulls(frame), results, 0)
        )
        t2 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.drop_nulls(frame), results, 1)
        )

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results[0].shape[0] == 2
        assert results[1].shape[0] == 2

    def test_concurrent_drop_duplicates(self, tmp_path):
        """drop_duplicates should run concurrently."""
        path = tmp_path / "dupes.csv"
        path.write_text("name,age\nAlice,30\nAlice,30\nBob,25\n")
        frame = ar.read_csv(str(path))

        results = [None, None]
        t1 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.drop_duplicates(frame), results, 0)
        )
        t2 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.drop_duplicates(frame), results, 1)
        )

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results[0].shape[0] == 2
        assert results[1].shape[0] == 2

    def test_concurrent_strip_whitespace(self, tmp_path):
        """strip_whitespace should run concurrently."""
        path = tmp_path / "ws.csv"
        path.write_text("name,city\n  Alice  , New York\n  Bob ,London\n")
        frame = ar.read_csv(str(path))

        results = [None, None]
        t1 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.strip_whitespace(frame), results, 0)
        )
        t2 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.strip_whitespace(frame), results, 1)
        )

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        df0 = ar.to_pandas(results[0])
        df1 = ar.to_pandas(results[1])
        assert df0["name"].iloc[0] == "Alice"
        assert df1["name"].iloc[0] == "Alice"

    def test_concurrent_normalize_case(self, tmp_path):
        """normalize_case should run concurrently."""
        path = tmp_path / "case.csv"
        path.write_text("name\nALICE\nBOB\nCHARLIE\n")
        frame = ar.read_csv(str(path))

        results = [None, None]
        t1 = threading.Thread(
            target=run_in_thread,
            args=(lambda: ar.normalize_case(frame, subset=["name"]), results, 0),
        )
        t2 = threading.Thread(
            target=run_in_thread,
            args=(lambda: ar.normalize_case(frame, subset=["name"]), results, 1),
        )

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        df0 = ar.to_pandas(results[0])
        assert df0["name"].iloc[0] == "alice"


class TestGILReleaseEdgeCases:
    def test_concurrent_read_invalid_path(self):
        """Concurrent reads with invalid path should raise errors safely."""
        results = [None, None]
        t1 = threading.Thread(
            target=run_in_thread,
            args=(lambda: ar.read_csv("nonexistent.csv"), results, 0),
        )
        t2 = threading.Thread(
            target=run_in_thread,
            args=(lambda: ar.read_csv("nonexistent.csv"), results, 1),
        )

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert isinstance(results[0], Exception)
        assert isinstance(results[1], Exception)

    def test_concurrent_read_empty_csv(self, tmp_path):
        """Concurrent reads on empty CSV should not crash."""
        path = tmp_path / "empty.csv"
        path.write_text("name,age\n")

        results = [None, None]
        t1 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.read_csv(str(path)), results, 0)
        )
        t2 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.read_csv(str(path)), results, 1)
        )

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results[0].shape[0] == 0
        assert results[1].shape[0] == 0

    def test_concurrent_scan_schema(self, tmp_path):
        """scan_schema should run concurrently without errors."""
        path = tmp_path / "schema.csv"
        path.write_text("name,age,score\nAlice,30,95.5\nBob,25,88.0\n")

        results = [None, None]
        t1 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.scan_csv(str(path)), results, 0)
        )
        t2 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.scan_csv(str(path)), results, 1)
        )

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert isinstance(results[0], dict)
        assert isinstance(results[1], dict)
        assert results[0]["name"] == results[1]["name"]

    def test_concurrent_drop_nulls_subset(self, tmp_path):
        """drop_nulls with subset should work concurrently."""
        path = tmp_path / "nulls.csv"
        path.write_text("name,age\nAlice,30\n,25\nCharlie,\nDiana,28\n")
        frame = ar.read_csv(str(path))

        results = [None, None]
        t1 = threading.Thread(
            target=run_in_thread,
            args=(lambda: ar.drop_nulls(frame, subset=["name"]), results, 0),
        )
        t2 = threading.Thread(
            target=run_in_thread,
            args=(lambda: ar.drop_nulls(frame, subset=["name"]), results, 1),
        )

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results[0].shape[0] == 3
        assert results[1].shape[0] == 3

    def test_mixed_concurrent_operations(self, tmp_path):
        """Different GIL-releasing ops should run concurrently without interference."""
        path = tmp_path / "data.csv"
        path.write_text("name,age\n  Alice  ,30\nAlice,30\nBob,25\n,20\n")
        frame = ar.read_csv(str(path))

        results = [None, None, None]
        t1 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.drop_nulls(frame), results, 0)
        )
        t2 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.strip_whitespace(frame), results, 1)
        )
        t3 = threading.Thread(
            target=run_in_thread, args=(lambda: ar.drop_duplicates(frame), results, 2)
        )

        t1.start()
        t2.start()
        t3.start()
        t1.join()
        t2.join()
        t3.join()

        assert results[2].shape[0] == 4
