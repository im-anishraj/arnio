import pandas as pd
import arnio as ar
import tracemalloc
import time

def benchmark():
    print("Generating large dataset...")
    # Create a 20M row dataframe (~320MB of memory)
    df = pd.DataFrame({
        'a': range(20000000),
        'b': range(20000000)
    })
    
    frame = ar.from_pandas(df)
    
    print("Starting trace...")
    tracemalloc.start()
    
    start_time = time.time()
    
    # Run a cleaning operation that would previously deep copy the whole frame
    _ = ar.safe_divide_columns(frame, 'a', 'b', 'ratio')
    
    current, peak = tracemalloc.get_traced_memory()
    end_time = time.time()
    
    print(f"Memory Peak: {peak / 10**6:.2f} MB")
    print(f"Execution Time: {end_time - start_time:.2f} seconds")
    
    tracemalloc.stop()

if __name__ == '__main__':
    benchmark()
