import pandas as pd

import arnio as ar


def test_frame_row_col_count():
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    frame = ar.from_pandas(df)
    assert frame.row_count == 3
    assert frame.column_count == 2
