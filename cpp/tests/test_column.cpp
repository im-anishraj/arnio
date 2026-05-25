#include <catch2/catch_test_macros.hpp>

#include "arnio/column.h"

using namespace arnio;

TEST_CASE("Column default construction", "[column]") {
    Column col("age", DType::INT64);
    REQUIRE(col.name() == "age");
    REQUIRE(col.dtype() == DType::INT64);
    REQUIRE(col.size() == 0);
}

TEST_CASE("Column push_back and at", "[column]") {
    Column col("score", DType::FLOAT64);
    col.push_back(double(3.14));
    col.push_back(double(2.71));

    REQUIRE(col.size() == 2);
    REQUIRE(col.at(0) == CellValue(double(3.14)));
    REQUIRE(col.at(1) == CellValue(double(2.71)));
}

TEST_CASE("Column push_null", "[column]") {
    Column col("name", DType::STRING);
    col.push_back(std::string("alice"));
    col.push_null();

    REQUIRE(col.size() == 2);
    REQUIRE(col.is_null(1) == true);
    REQUIRE(col.is_null(0) == false);
}

TEST_CASE("Column clone", "[column]") {
    Column col("val", DType::INT64);
    col.push_back(int64_t(42));
    col.push_null();

    Column cloned = col.clone();
    REQUIRE(cloned.name() == "val");
    REQUIRE(cloned.size() == 2);
    REQUIRE(cloned.at(0) == CellValue(int64_t(42)));
    REQUIRE(cloned.is_null(1) == true);
}

TEST_CASE("Column NULL_TYPE has zero size", "[column]") {
    Column col("empty", DType::NULL_TYPE);
    REQUIRE(col.size() == 0);
}

TEST_CASE("Inconsistent column throws on operations", "[column]") {
    ColumnData bad_data = std::vector<std::string>{"hello"};
    Column bad("x", DType::INT64, std::move(bad_data), std::vector<bool>{false});

    REQUIRE_THROWS_AS(bad.data(), std::logic_error);
    REQUIRE_THROWS_AS(bad.clone(), std::logic_error);
    REQUIRE_THROWS_AS(bad.at(0), std::logic_error);
    REQUIRE_THROWS_AS(bad.push_null(), std::logic_error);
    REQUIRE_THROWS_AS(bad.memory_usage(), std::logic_error);
}

TEST_CASE("Column bool memory layout is independent per element", "[column]") {
    Column col("flags", DType::BOOL);
    col.push_back(bool(true));
    col.push_back(bool(false));
    col.push_back(bool(true));

    REQUIRE(col.at(0) == CellValue(bool(true)));
    REQUIRE(col.at(1) == CellValue(bool(false)));
    REQUIRE(col.at(2) == CellValue(bool(true)));
    REQUIRE(col.size() == 3);
}

TEST_CASE("push_back string into numeric column keeps data aligned with null mask", "[column]") {
    Column int_col("integer", DType::INT64);
    int_col.push_back(std::string("hello"));
    REQUIRE(int_col.size() == 1);
    REQUIRE(int_col.null_mask().size() == 1);

    Column dbl_col("double", DType::FLOAT64);
    dbl_col.push_back(std::string("hello"));
    REQUIRE(dbl_col.size() == 1);
    REQUIRE(dbl_col.null_mask().size() == 1);

    Column bl_col("bool", DType::BOOL);
    bl_col.push_back(std::string("hello"));
    REQUIRE(bl_col.size() == 1);
    REQUIRE(bl_col.null_mask().size() == 1);
}