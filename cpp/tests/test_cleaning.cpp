#include <catch2/catch_test_macros.hpp>
#include <cmath>    // std::isnan
#include <cstdint>  // uint64_t
#include <cstring>  // std::memcpy

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
// ── drop_duplicates: hash-path correctness tests ─────────────────────────────

TEST_CASE("drop_duplicates deduplicates int column keep=first", "[cleaning][dedup]") {
    Column c("x", DType::INT64);
    c.push_back(int64_t(1));
    c.push_back(int64_t(2));
    c.push_back(int64_t(1));  // duplicate of row 0
    c.push_back(int64_t(3));
    Frame f;
    f.add_column(std::move(c));

    Frame result = drop_duplicates(f, std::nullopt, "first");
    REQUIRE(result.num_rows() == 3);
    REQUIRE(result.column("x").at(0) == CellValue(int64_t(1)));
    REQUIRE(result.column("x").at(1) == CellValue(int64_t(2)));
    REQUIRE(result.column("x").at(2) == CellValue(int64_t(3)));
}

TEST_CASE("drop_duplicates deduplicates int column keep=last", "[cleaning][dedup]") {
    Column c("x", DType::INT64);
    c.push_back(int64_t(1));
    c.push_back(int64_t(2));
    c.push_back(int64_t(1));  // duplicate — last occurrence wins
    Frame f;
    f.add_column(std::move(c));

    Frame result = drop_duplicates(f, std::nullopt, "last");
    REQUIRE(result.num_rows() == 2);
    REQUIRE(result.column("x").at(0) == CellValue(int64_t(2)));
    REQUIRE(result.column("x").at(1) == CellValue(int64_t(1)));
}

TEST_CASE("drop_duplicates deduplicates int column keep=none", "[cleaning][dedup]") {
    Column c("x", DType::INT64);
    c.push_back(int64_t(1));
    c.push_back(int64_t(2));
    c.push_back(int64_t(1));  // duplicate — both rows dropped
    c.push_back(int64_t(3));
    Frame f;
    f.add_column(std::move(c));

    Frame result = drop_duplicates(f, std::nullopt, "none");
    REQUIRE(result.num_rows() == 2);
    REQUIRE(result.column("x").at(0) == CellValue(int64_t(2)));
    REQUIRE(result.column("x").at(1) == CellValue(int64_t(3)));
}

TEST_CASE("drop_duplicates deduplicates float column", "[cleaning][dedup]") {
    Column c("v", DType::FLOAT64);
    c.push_back(double(1.5));
    c.push_back(double(2.5));
    c.push_back(double(1.5));  // duplicate
    Frame f;
    f.add_column(std::move(c));

    Frame result = drop_duplicates(f, std::nullopt, "first");
    REQUIRE(result.num_rows() == 2);
    REQUIRE(result.column("v").at(0) == CellValue(double(1.5)));
    REQUIRE(result.column("v").at(1) == CellValue(double(2.5)));
}

TEST_CASE("drop_duplicates deduplicates string column", "[cleaning][dedup]") {
    Column c("s", DType::STRING);
    c.push_back(std::string("apple"));
    c.push_back(std::string("banana"));
    c.push_back(std::string("apple"));  // duplicate
    c.push_back(std::string("cherry"));
    Frame f;
    f.add_column(std::move(c));

    Frame result = drop_duplicates(f, std::nullopt, "first");
    REQUIRE(result.num_rows() == 3);
    REQUIRE(result.column("s").at(0) == CellValue(std::string("apple")));
    REQUIRE(result.column("s").at(1) == CellValue(std::string("banana")));
    REQUIRE(result.column("s").at(2) == CellValue(std::string("cherry")));
}

TEST_CASE("drop_duplicates deduplicates mixed-type columns", "[cleaning][dedup]") {
    // Two columns: int + string. Row is duplicate only if BOTH columns match.
    Column ci("id", DType::INT64);
    ci.push_back(int64_t(1));
    ci.push_back(int64_t(1));  // same id …
    ci.push_back(int64_t(2));
    ci.push_back(int64_t(1));  // full duplicate of row 0

    Column cs("label", DType::STRING);
    cs.push_back(std::string("a"));
    cs.push_back(std::string("b"));  // different label → NOT a duplicate
    cs.push_back(std::string("a"));
    cs.push_back(std::string("a"));  // matches row 0 exactly → duplicate

    Frame f;
    f.add_column(std::move(ci));
    f.add_column(std::move(cs));

    Frame result = drop_duplicates(f, std::nullopt, "first");
    REQUIRE(result.num_rows() == 3);
}

TEST_CASE("drop_duplicates type-safety: int 1 and bool true are not duplicates",
          "[cleaning][dedup]") {
    // INT64(1) and BOOL(true) share the same binary value (0x01) but use
    // different hash seeds (^0x01 vs ^0x03) so they must never collide.
    // Each frame below has a genuine intra-type duplicate, verifying that
    // same-type duplicates ARE collapsed while cross-type values remain separate.
    Column ci("x", DType::INT64);
    ci.push_back(int64_t(1));
    ci.push_back(int64_t(1));  // genuine duplicate
    Frame fi;
    fi.add_column(std::move(ci));
    REQUIRE(drop_duplicates(fi, std::nullopt, "first").num_rows() == 1);

    Column cb("x", DType::BOOL);
    cb.push_back(bool(true));
    cb.push_back(bool(true));  // genuine duplicate
    Frame fb;
    fb.add_column(std::move(cb));
    REQUIRE(drop_duplicates(fb, std::nullopt, "first").num_rows() == 1);
}

TEST_CASE("drop_duplicates column-order sensitivity: (A,B) != (B,A)", "[cleaning][dedup]") {
    // hash_row() uses FNV multiply-xor chaining so column order is significant.
    // Row 0: (id=1, label="2") and Row 1: (id=2, label="1") have the same
    // multiset of values but different assignments — must NOT be collapsed.
    Column ci("id", DType::INT64);
    ci.push_back(int64_t(1));
    ci.push_back(int64_t(2));

    Column cs("label", DType::STRING);
    cs.push_back(std::string("2"));
    cs.push_back(std::string("1"));

    Frame f;
    f.add_column(std::move(ci));
    f.add_column(std::move(cs));

    Frame result = drop_duplicates(f, std::nullopt, "first");
    REQUIRE(result.num_rows() == 2);
}

TEST_CASE("drop_duplicates null rows treated as equal", "[cleaning][dedup]") {
    Column c("x", DType::INT64);
    c.push_null();
    c.push_null();  // second null — duplicate
    c.push_back(int64_t(5));
    Frame f;
    f.add_column(std::move(c));

    Frame result = drop_duplicates(f, std::nullopt, "first");
    REQUIRE(result.num_rows() == 2);
    REQUIRE(result.column("x").is_null(0));
    REQUIRE(result.column("x").at(1) == CellValue(int64_t(5)));
}

// ── NaN regression tests ──────────────────────────────────────────────────────
// hash_cell() must normalize NaN before hashing so that two NaN values with
// different bit-patterns (different payloads) produce the same hash.
// combine_cell_to_string / serialize_cell render *all* NaN values as the string
// "nan", so row_key() treats them as equal — hash_cell() must agree or the
// fast hash-miss path will bypass the equality check and keep both rows.

// Helper: construct a double from raw bits without UB.
static double bits_to_double(uint64_t bits) {
    double v;
    std::memcpy(&v, &bits, sizeof(v));
    return v;
}

TEST_CASE("drop_duplicates NaN payloads treated as equal (keep=first)", "[cleaning][dedup][nan]") {
    // Three positive NaN values with different payloads: raw bytes differ, but
    // %.17g serialises all positive NaN variants as "nan", so row_key() treats
    // them as equal duplicates.
    // NOTE: negative NaN is intentionally excluded — glibc's %.17g renders it
    // as "-nan", giving a different row_key() and making it a distinct value.
    // Sticking to positive-payload NaNs keeps the test platform-independent.
    double nan1 = bits_to_double(0x7FF8000000000000ULL);  // canonical quiet NaN
    double nan2 = bits_to_double(0x7FF8000000000001ULL);  // different payload
    double nan3 = bits_to_double(0x7FF8000000000002ULL);  // yet another payload

    Column c("v", DType::FLOAT64);
    c.push_back(nan1);
    c.push_back(nan2);  // duplicate of nan1
    c.push_back(double(1.0));
    c.push_back(nan3);  // also a duplicate of nan1

    Frame f;
    f.add_column(std::move(c));

    Frame result = drop_duplicates(f, std::nullopt, "first");
    // Only nan1 (first occurrence) and 1.0 survive.
    REQUIRE(result.num_rows() == 2);
    REQUIRE(std::isnan(std::get<double>(result.column("v").at(0))));
    REQUIRE(result.column("v").at(1) == CellValue(double(1.0)));
}

TEST_CASE("drop_duplicates NaN payloads treated as equal (keep=last)", "[cleaning][dedup][nan]") {
    double nan1 = bits_to_double(0x7FF8000000000000ULL);
    double nan2 = bits_to_double(0x7FF8000000000002ULL);

    Column c("v", DType::FLOAT64);
    c.push_back(double(2.0));
    c.push_back(nan1);
    c.push_back(nan2);  // duplicate of nan1; last occurrence wins

    Frame f;
    f.add_column(std::move(c));

    Frame result = drop_duplicates(f, std::nullopt, "last");
    REQUIRE(result.num_rows() == 2);
    REQUIRE(result.column("v").at(0) == CellValue(double(2.0)));
    REQUIRE(std::isnan(std::get<double>(result.column("v").at(1))));
}

TEST_CASE("drop_duplicates NaN payloads treated as equal (keep=none)", "[cleaning][dedup][nan]") {
    double nan1 = bits_to_double(0x7FF8000000000000ULL);
    double nan2 = bits_to_double(0x7FF8000000000003ULL);

    Column c("v", DType::FLOAT64);
    c.push_back(nan1);
    c.push_back(double(3.0));
    c.push_back(nan2);  // duplicate of nan1 — both NaN rows must be dropped

    Frame f;
    f.add_column(std::move(c));

    Frame result = drop_duplicates(f, std::nullopt, "none");
    REQUIRE(result.num_rows() == 1);
    REQUIRE(result.column("v").at(0) == CellValue(double(3.0)));
}
