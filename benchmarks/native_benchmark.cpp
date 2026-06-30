#include <iostream>
#include <chrono>
#include <vector>
#include <string>
#include "arnio/cleaning.h"
#include "arnio/frame.h"
#include "arnio/column.h"

using namespace arnio;

int main() {
    // We use a frame with 0 rows to eliminate data-processing time.
    // This isolates the exact argument passing overhead.
    Frame frame;
    Column col("col1", DType::STRING);
    frame.add_column(col);

    const int iterations = 1000000;
    const int samples = 5;

    std::cout << "======================================================\n";
    std::cout << "Native C++ Benchmark: normalize_case (std::string_view)\n";
    std::cout << "Iterations per sample: " << iterations << " | Total samples: " << samples << "\n";
    std::cout << "======================================================\n\n";

    // Warmup
    auto warmup = normalize_case(frame, std::nullopt, "lower");

    double total_time = 0.0;
    for (int s = 0; s < samples; ++s) {
        auto start = std::chrono::high_resolution_clock::now();

        int dummy_sum = 0;
        for (int i = 0; i < iterations; ++i) {
            // Passing string literal triggers std::string_view conversion vs std::string allocation
            auto res = normalize_case(frame, std::nullopt, "lower");
            dummy_sum += res.num_cols(); // Consume result to prevent compiler optimizing the loop away
        }

        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> diff = end - start;
        std::cout << "  Sample " << s + 1 << ": " << diff.count() << " seconds\n";
        total_time += diff.count();

        if (dummy_sum == 0) break; // Use the sum so the compiler doesn't delete it
    }

    std::cout << "------------------------------------------------------\n";
    std::cout << "AVERAGE TIME: " << total_time / samples << " seconds\n";
    std::cout << "======================================================\n";

    return 0;
}