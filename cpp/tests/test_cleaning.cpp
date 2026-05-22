#include <catch2/catch_test_macros.hpp>

#include "arnio/cleaning.h"

using namespace arnio;

static Frame make_string_frame() {
    Column c1("name", DType::STRING);
    c1.push_back(std::string("  alice  "));
    c1.push_back(std::string("  BOB  "));
    c1.push_null();

    Column c2("city", DType::STRING);
    c2.push_back(std::string("  Delhi  "));
    c2.push_back(std::string("MUMBAI"));
    c2.push_back(std::string("pune"));

    Frame f;
    f.add_column(std::move(c1));
    f.add_column(std::move(c2));
    return f;
}

static Frame make_null_frame() {
    Column c1("val", DType::INT64);
    c1.push_back(int64_t(10));
    c1.push_null();
    c1.push_back(int64_t(30));

    Column c2("tag", DType::STRING);
    c2.push_back(std::string("a"));
    c2.push_back(std::string("b"));
    c2.push_null();

    Frame f;
    f.add_column(std::move(c1));
    f.add_column(std::move(c2));
    return f;
}

TEST_CASE("strip_whitespace removes leading and trailing spaces", "[cleaning]") {
    Frame f = make_string_frame();
    Frame result = strip_whitespace(f);

    REQUIRE(result.column("name").at(0) == CellValue(std::string("alice")));
    REQUIRE(result.column("name").at(1) == CellValue(std::string("BOB")));
    REQUIRE(result.column("city").at(0) == CellValue(std::string("Delhi")));
}

TEST_CASE("strip_whitespace preserves nulls", "[cleaning]") {
    Frame f = make_string_frame();
    Frame result = strip_whitespace(f);
    REQUIRE(result.column("name").is_null(2) == true);
}

TEST_CASE("strip_whitespace subset only affects specified columns", "[cleaning]") {
    Frame f = make_string_frame();
    Frame result = strip_whitespace(f, std::vector<std::string>{"name"});

    REQUIRE(result.column("name").at(0) == CellValue(std::string("alice")));
    REQUIRE(result.column("city").at(0) == CellValue(std::string("  Delhi  ")));
}

TEST_CASE("normalize_case lower", "[cleaning]") {
    Frame f = make_string_frame();
    Frame result = normalize_case(f, std::nullopt, "lower");

    REQUIRE(result.column("name").at(1) == CellValue(std::string("  bob  ")));
    REQUIRE(result.column("city").at(1) == CellValue(std::string("mumbai")));
}

TEST_CASE("normalize_case upper", "[cleaning]") {
    Frame f = make_string_frame();
    Frame result = normalize_case(f, std::nullopt, "upper");

    REQUIRE(result.column("name").at(0) == CellValue(std::string("  ALICE  ")));
    REQUIRE(result.column("city").at(2) == CellValue(std::string("PUNE")));
}

TEST_CASE("normalize_case preserves nulls", "[cleaning]") {
    Frame f = make_string_frame();
    Frame result = normalize_case(f);
    REQUIRE(result.column("name").is_null(2) == true);
}

TEST_CASE("drop_nulls removes rows with any null", "[cleaning]") {
    Frame f = make_null_frame();
    Frame result = drop_nulls(f);
    REQUIRE(result.num_rows() == 1);
    REQUIRE(result.column("val").at(0) == CellValue(int64_t(10)));
}

TEST_CASE("drop_nulls subset only checks specified columns", "[cleaning]") {
    Frame f = make_null_frame();
    Frame result = drop_nulls(f, std::vector<std::string>{"val"});
    REQUIRE(result.num_rows() == 2);
}

TEST_CASE("fill_nulls replaces nulls in int column", "[cleaning]") {
    Frame f = make_null_frame();
    Frame result = fill_nulls(f, CellValue(int64_t(99)), std::vector<std::string>{"val"});

    REQUIRE(result.column("val").is_null(1) == false);
    REQUIRE(result.column("val").at(1) == CellValue(int64_t(99)));
}

TEST_CASE("drop_duplicates removes repeated rows", "[cleaning]") {
    Column c1("x", DType::INT64);
    c1.push_back(int64_t(1));
    c1.push_back(int64_t(1));
    c1.push_back(int64_t(2));

    Frame f;
    f.add_column(std::move(c1));

    Frame result = drop_duplicates(f);
    REQUIRE(result.num_rows() == 2);
}