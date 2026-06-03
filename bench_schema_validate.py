import pandas as pd
import numpy as np
from arnio.schema import Schema

def make_dataset(n=1_000_000):
    return pd.DataFrame({
        "id": np.arange(n),
        "age": np.random.randint(18, 80, n),
        "name": ["user"] * n,
        "salary": np.random.rand(n) * 100000
    })

def run():
    import numpy as np
    import pandas as pd

    from arnio.convert import from_pandas
    from arnio.schema import Schema

    pd_df = pd.DataFrame({
        "id": np.arange(200_000),   # REDUCED SIZE (IMPORTANT)
        "age": np.random.randint(18, 80, 200_000),
        "name": ["user"] * 200_000,
        "salary": np.random.rand(200_000) * 100000
    })

    df = from_pandas(pd_df)

    schema = Schema({})

    schema.validate(df)