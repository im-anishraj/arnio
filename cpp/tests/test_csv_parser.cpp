#include <catch2/catch_test_macros.hpp>
#include <fstream>

#include "arnio/csv_reader.h"

using namespace arnio;

TEST_CASE("parse_line splits basic CSV row", "[csv_parser]") {
    CsvParser parser;
    auto fields = parser.parse_line("alice,30,delhi");
    REQUIRE(fields.size() == 3);
    REQUIRE(fields[0] == "alice");
    REQUIRE(fields[1] == "30");
    REQUIRE(fields[2] == "delhi");
}

TEST_CASE("parse_line handles quoted fields", "[csv_parser]") {
    CsvParser parser;
    auto fields = parser.parse_line("\"alice, bob\",30,delhi");
    REQUIRE(fields.size() == 3);
    REQUIRE(fields[0] == "alice, bob");
}

TEST_CASE("parse_line handles escaped quotes inside quoted field", "[csv_parser]") {
    CsvParser parser;
    auto fields = parser.parse_line("\"she said \"\"hello\"\"\",42");
    REQUIRE(fields.size() == 2);
    REQUIRE(fields[0] == "she said \"hello\"");
}

TEST_CASE("parse_line handles empty fields", "[csv_parser]") {
    CsvParser parser;
    auto fields = parser.parse_line("a,,c");
    REQUIRE(fields.size() == 3);
    REQUIRE(fields[1] == "");
}

TEST_CASE("parse_line respects custom delimiter", "[csv_parser]") {
    CsvConfig cfg;
    cfg.delimiter = ';';
    CsvParser parser(cfg);
    auto fields = parser.parse_line("alice;30;delhi");
    REQUIRE(fields.size() == 3);
    REQUIRE(fields[1] == "30");
}

TEST_CASE("infer_type detects INT64", "[csv_parser]") {
    CsvParser parser;
    REQUIRE(parser.infer_type("42") == DType::INT64);
    REQUIRE(parser.infer_type("-7") == DType::INT64);
    REQUIRE(parser.infer_type("0") == DType::INT64);
}

TEST_CASE("infer_type detects FLOAT64", "[csv_parser]") {
    CsvParser parser;
    REQUIRE(parser.infer_type("3.14") == DType::FLOAT64);
    REQUIRE(parser.infer_type("-0.5") == DType::FLOAT64);
}

TEST_CASE("infer_type detects BOOL", "[csv_parser]") {
    CsvParser parser;
    REQUIRE(parser.infer_type("true") == DType::BOOL);
    REQUIRE(parser.infer_type("false") == DType::BOOL);
    REQUIRE(parser.infer_type("True") == DType::BOOL);
}

TEST_CASE("infer_type detects STRING", "[csv_parser]") {
    CsvParser parser;
    REQUIRE(parser.infer_type("alice") == DType::STRING);
    REQUIRE(parser.infer_type("123abc") == DType::STRING);
}

TEST_CASE("infer_type detects NULL_TYPE on empty string", "[csv_parser]") {
    CsvParser parser;
    REQUIRE(parser.infer_type("") == DType::NULL_TYPE);
}

TEST_CASE("promote_type INT64 + FLOAT64 = FLOAT64", "[csv_parser]") {
    REQUIRE(CsvParser::promote_type(DType::INT64, DType::FLOAT64) == DType::FLOAT64);
}

TEST_CASE("promote_type anything + STRING = STRING", "[csv_parser]") {
    REQUIRE(CsvParser::promote_type(DType::INT64, DType::STRING) == DType::STRING);
    REQUIRE(CsvParser::promote_type(DType::FLOAT64, DType::STRING) == DType::STRING);
    REQUIRE(CsvParser::promote_type(DType::BOOL, DType::STRING) == DType::STRING);
}

TEST_CASE("promote_type NULL_TYPE + INT64 = INT64", "[csv_parser]") {
    REQUIRE(CsvParser::promote_type(DType::NULL_TYPE, DType::INT64) == DType::INT64);
}

TEST_CASE("is_null_sentinel default only matches empty string", "[csv_parser]") {
    // Known limitation: default config only treats empty string as null.
    // "NA", "N/A", "null" require explicit CsvConfig::null_values. See issue #92.
    CsvParser parser;
    REQUIRE(parser.is_null_sentinel("") == true);
    REQUIRE(parser.is_null_sentinel("NA") == false);
    REQUIRE(parser.is_null_sentinel("alice") == false);
}

TEST_CASE("is_null_sentinel respects custom null_values config", "[csv_parser]") {
    CsvConfig cfg;
    cfg.null_values = std::vector<std::string>{"NA", "N/A", "null"};
    CsvParser parser(cfg);
    REQUIRE(parser.is_null_sentinel("NA") == true);
    REQUIRE(parser.is_null_sentinel("N/A") == true);
    REQUIRE(parser.is_null_sentinel("null") == true);
    REQUIRE(parser.is_null_sentinel("NULL") == true);
    REQUIRE(parser.is_null_sentinel("alice") == false);
}