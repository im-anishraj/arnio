import time
import arnio

def run_benchmark():
    # 1. Use a TINY frame. We want the data processing to take almost zero time
    # so we can strictly measure the overhead of the function call boundary.
    data = {"col1": ["a", "b", "c"]}
    frame = arnio.from_dict(data)

    iterations = 500_000
    print(f"Benchmarking normalize_case call boundary ({iterations} iterations)...")

    # 2. Warmup run
    arnio.normalize_case(frame, case_type="lower")

    # 3. Measure the Python-to-C++ boundary overhead
    start_time = time.perf_counter()
    
    # By looping 500,000 times, we force Python to send the string "lower" 
    # to C++ 500,000 times. This is exactly what std::string_view optimizes.
    for _ in range(iterations):
        arnio.normalize_case(frame, case_type="lower")
        
    end_time = time.perf_counter()
    
    elapsed = end_time - start_time
    print(f"Total time for {iterations} boundary crossings: {elapsed:.5f} seconds")

if __name__ == "__main__":
    run_benchmark()