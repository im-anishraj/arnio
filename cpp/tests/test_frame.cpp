#include <catch2/catch_test_macros.hpp>
#include <stdexcept>

#include "arnio/frame.h"

using namespace arnio;

static Frame make_simple_frame() {
    Column c1("id", DType::INT64);
    c1.push_back(int64_t(1));
    c1.push_back(int64_t(2));

    Column c2("name", DType::STRING);
    c2.push_back(std::string("alice"));
    c2.push_back(std::string("bob"));

    Frame f;
    f.add_column(std::move(c1));
    f.add_column(std::move(c2));
    return f;
}

TEST_CASE("Frame default construction", "[frame]") {
    Frame f;
    REQUIRE(f.num_rows() == 0);
    REQUIRE(f.num_cols() == 0);
}

TEST_CASE("Frame shape after adding columns", "[frame]") {
    Frame f = make_simple_frame();
    REQUIRE(f.num_rows() == 2);
    REQUIRE(f.num_cols() == 2);
    REQUIRE(f.shape() == std::make_pair(size_t(2), size_t(2)));
}

TEST_CASE("Frame column access by name and index", "[frame]") {
    Frame f = make_simple_frame();

    REQUIRE(f.column(0).name() == "id");
    REQUIRE(f.column("name").name() == "name");
    REQUIRE(f.has_column("id") == true);
    REQUIRE(f.has_column("missing") == false);
}

TEST_CASE("Frame column_names returns correct order", "[frame]") {
    Frame f = make_simple_frame();
    auto names = f.column_names();
    REQUIRE(names.size() == 2);
    REQUIRE(names[0] == "id");
    REQUIRE(names[1] == "name");
}

TEST_CASE("Frame clone is independent", "[frame]") {
    Frame f = make_simple_frame();
    Frame cloned = f.clone();

    REQUIRE(cloned.num_rows() == f.num_rows());
    REQUIRE(cloned.num_cols() == f.num_cols());
    REQUIRE(cloned.column("id").at(0) == CellValue(int64_t(1)));
}

TEST_CASE("Frame with 0 columns has 0 rows", "[frame]") {
    Frame f;
    REQUIRE(f.num_rows() == 0);
    REQUIRE(f.num_cols() == 0);
    REQUIRE(f.column_names().empty());
}

TEST_CASE("Frame::add_column throws on duplicate column name", "[frame]") {
    Frame f;
    Column first("price", DType::INT64);
    first.push_back(int64_t(10));
    Column second("price", DType::INT64);
    second.push_back(int64_t(20));

    f.add_column(std::move(first));

    REQUIRE_THROWS_AS(f.add_column(std::move(second)), std::invalid_argument);
    REQUIRE(f.num_cols() == 1);
    REQUIRE(f.column("price").at(0) == CellValue(int64_t(10)));
}

TEST_CASE("Frame::add_column succeeds for distinct column names", "[frame]") {
    Frame f;
    Column price("price", DType::INT64);
    price.push_back(int64_t(10));
    Column quantity("quantity", DType::INT64);
    quantity.push_back(int64_t(2));

    REQUIRE_NOTHROW(f.add_column(std::move(price)));
    REQUIRE_NOTHROW(f.add_column(std::move(quantity)));
    REQUIRE(f.num_cols() == 2);
    REQUIRE(f.has_column("price") == true);
    REQUIRE(f.has_column("quantity") == true);
}

TEST_CASE("Frame::describe includes boolean column metrics", "[frame][describe]") {
    Column flags("flag", DType::BOOL);
    flags.push_back(true);
    flags.push_back(false);
    flags.push_null();
    flags.push_back(true);

    Frame f;
    f.add_column(std::move(flags));

    auto summary = f.describe();
    REQUIRE(summary.size() == 1);
    REQUIRE(summary[0].first == "flag");

    const auto& stats = summary[0].second;
    REQUIRE(stats.size() == 5);
    REQUIRE(stats[0] == std::make_pair(std::string("count"), 3.0));
    REQUIRE(stats[1] == std::make_pair(std::string("nulls"), 1.0));
    REQUIRE(stats[2] == std::make_pair(std::string("true"), 2.0));
    REQUIRE(stats[3] == std::make_pair(std::string("false"), 1.0));
    REQUIRE(stats[4].first == "true_ratio");
    REQUIRE(stats[4].second == 2.0 / 3.0);
}

TEST_CASE("Frame::describe reports empty boolean summaries deterministically",
          "[frame][describe]") {
    Column flags("flag", DType::BOOL);

    Frame f;
    f.add_column(std::move(flags));

    auto summary = f.describe();
    REQUIRE(summary.size() == 1);

    const auto& stats = summary[0].second;
    REQUIRE(stats[0] == std::make_pair(std::string("count"), 0.0));
    REQUIRE(stats[1] == std::make_pair(std::string("nulls"), 0.0));
    REQUIRE(stats[2] == std::make_pair(std::string("true"), 0.0));
    REQUIRE(stats[3] == std::make_pair(std::string("false"), 0.0));
    REQUIRE(stats[4] == std::make_pair(std::string("true_ratio"), 0.0));
}
