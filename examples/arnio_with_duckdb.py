"""
Arnio + DuckDB: Clean/validate data before querying.
----------------------------------------------------
This example shows how to use Arnio to clean messy data and
then load it into DuckDB for SQL-based analytics.

Run:
    python examples/arnio_with_duckdb.py

Requires:
    pip install duckdb
"""

import io

try:
    import duckdb
except ImportError:
    print("DuckDB is not installed. Run: pip install duckdb")
    raise SystemExit(0)

import arnio as ar


def main():
    # 1. Synthetic messy CSV: sales records
    raw_csv = (
        "order_id,product,quantity,unit_price,region\n"
        "O1, Widget A ,10,5.99, North \n"
        "O2,Widget B,,3.49,South\n"   # missing quantity
        "O3, Gadget C ,5,12.00,EAST\n"
        "O1, Widget A ,10,5.99,North\n"  # duplicate
        "O4,Gadget D,2,,West\n"          # missing unit_price
        "O5,Widget E,7,8.50,South\n"
    )

    # 2. Load and clean with Arnio
    frame = ar.read_csv(io.StringIO(raw_csv))
    clean_frame = ar.pipeline(
        frame,
        [
            ("strip_whitespace",),
            ("normalize_case", {"case_type": "title"}),
            ("fill_nulls", {"value": 0.0, "subset": ["quantity", "unit_price"]}),
            ("drop_duplicates",),
        ],
    )
    df = ar.to_pandas(clean_frame)
    print("--- Cleaned Data ---")
    print(df)

    # 3. Register the cleaned DataFrame with DuckDB and run SQL queries
    con = duckdb.connect()
    con.register("sales", df)

    print("\n--- Total Revenue by Region ---")
    result = con.execute(
        "SELECT region, ROUND(SUM(quantity * unit_price), 2) AS total_revenue "
        "FROM sales GROUP BY region ORDER BY total_revenue DESC"
    ).df()
    print(result)

    print("\n--- Top Products by Quantity Sold ---")
    result2 = con.execute(
        "SELECT product, SUM(quantity) AS total_qty "
        "FROM sales GROUP BY product ORDER BY total_qty DESC LIMIT 5"
    ).df()
    print(result2)

    con.close()


if __name__ == "__main__":
    main()
