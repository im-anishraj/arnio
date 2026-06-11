import time
import arnio

def run_benchmark():
    # 1. Tiny frame to isolate the Python-to-C++ call boundary overhead
    data = {"col1": ["a", "b", "c"]}
    frame = arnio.from_dict(data)

    iterations_per_sample = 100_000
    samples = 5

    print("======================================================")
    print("Benchmarking normalize_case (std::string_view overhead)")
    print(f"Iterations per sample: {iterations_per_sample} | Total samples: {samples}")
    print("======================================================\n")

    # 2. Warmup run (gets the code into CPU cache)
    _ = arnio.normalize_case(frame, case_type="lower")

    # 3. Run repeated samples
    times = []
    for i in range(samples):
        start_time = time.perf_counter()
        
        for _ in range(iterations_per_sample):
            _ = arnio.normalize_case(frame, case_type="lower")
            
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        times.append(elapsed)
        print(f"  Sample {i+1}: {elapsed:.4f} seconds")

    avg_time = sum(times) / len(times)
    print("------------------------------------------------------")
    print(f"AVERAGE TIME: {avg_time:.4f} seconds")
    print("======================================================\n")

if __name__ == "__main__":
    run_benchmark()