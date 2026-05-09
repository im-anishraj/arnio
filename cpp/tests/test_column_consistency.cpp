#include "arnio/column.h"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

static int failures = 0;

static void check(bool condition, const char* description) {
    if (!condition) {
        std::cerr << "FAIL: " << description << std::endl;
        ++failures;
    }
}

int main() {
    using namespace arnio;

    // Construct an inconsistent column: dtype=INT64 but data holds strings.
    ColumnData bad_data = std::vector<std::string>{"hello"};
    Column inconsistent("test", DType::INT64, std::move(bad_data),
                        std::vector<bool>{false});

    // -- clone() ----------------------------------------------------------
    {
        bool threw = false;
        try {
            auto cloned = inconsistent.clone();
        } catch (const std::logic_error&) {
            threw = true;
        }
        check(threw, "clone() should throw std::logic_error on inconsistent column");
    }

    // -- at() -------------------------------------------------------------
    {
        bool threw = false;
        try {
            (void)inconsistent.at(0);
        } catch (const std::logic_error&) {
            threw = true;
        }
        check(threw, "at() should throw on inconsistent column");
    }

    // -- push_back() ------------------------------------------------------
    {
        bool threw = false;
        try {
            inconsistent.push_back(std::string("x"));
        } catch (const std::logic_error&) {
            threw = true;
        }
        check(threw, "push_back() should throw on inconsistent column");
    }

    // -- push_null() ------------------------------------------------------
    {
        bool threw = false;
        try {
            inconsistent.push_null();
        } catch (const std::logic_error&) {
            threw = true;
        }
        check(threw, "push_null() should throw on inconsistent column");
    }

    // -- data() -----------------------------------------------------------
    {
        bool threw = false;
        try {
            (void)inconsistent.data();
        } catch (const std::logic_error&) {
            threw = true;
        }
        check(threw, "data() should throw on inconsistent column");
    }

    // -- memory_usage() ---------------------------------------------------
    {
        bool threw = false;
        try {
            (void)inconsistent.memory_usage();
        } catch (const std::logic_error&) {
            threw = true;
        }
        check(threw, "memory_usage() should throw on inconsistent column");
    }

    // -- Sanity: consistent column does NOT throw -------------------------
    {
        Column consistent("ok", DType::STRING);
        consistent.push_back(std::string("world"));
        try {
            auto cloned = consistent.clone();
            check(cloned.at(0) == CellValue(std::string("world")),
                  "clone() on consistent column should work");
        } catch (const std::logic_error&) {
            check(false, "clone() should not throw on consistent column");
        }
    }

    if (failures == 0) {
        std::cout << "All tests passed." << std::endl;
        return 0;
    }
    std::cerr << failures << " test(s) failed." << std::endl;
    return 1;
}
