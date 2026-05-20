#include "arnio/frame.h"

#include <stdexcept>

namespace arnio {

Frame::Frame(size_t row_count) : row_count_(row_count), row_count_known_(true) {}

Frame::Frame(std::vector<Column> columns) : columns_(std::move(columns)) {
    if (!columns_.empty()) {
        row_count_ = columns_[0].size();
        for (const auto& col : columns_) {
            validate_column_size(col);
        }
    }
    row_count_known_ = true;
    rebuild_index();
}

Frame::Frame(size_t row_count, std::vector<Column> columns)
    : columns_(std::move(columns)), row_count_(row_count), row_count_known_(true) {
    for (const auto& col : columns_) {
        validate_column_size(col);
    }
    rebuild_index();
}

std::pair<size_t, size_t> Frame::shape() const { return {num_rows(), num_cols()}; }

size_t Frame::num_rows() const { return row_count_; }

size_t Frame::num_cols() const { return columns_.size(); }

std::vector<std::string> Frame::column_names() const {
    std::vector<std::string> names;
    names.reserve(columns_.size());
    for (const auto& col : columns_) {
        names.push_back(col.name());
    }
    return names;
}

std::unordered_map<std::string, std::string> Frame::dtypes() const {
    std::unordered_map<std::string, std::string> result;
    for (const auto& col : columns_) {
        result[col.name()] = dtype_to_string(col.dtype());
    }
    return result;
}

size_t Frame::memory_usage() const {
    size_t usage = sizeof(Frame);
    for (const auto& col : columns_) {
        usage += col.memory_usage();
    }
    return usage;
}

const Column& Frame::column(size_t idx) const {
    if (idx >= columns_.size()) {
        throw std::out_of_range("Column index out of range");
    }
    return columns_[idx];
}

const Column& Frame::column(const std::string& name) const {
    auto it = name_index_.find(name);
    if (it == name_index_.end()) {
        throw std::out_of_range("Column not found: " + name);
    }
    return columns_[it->second];
}

bool Frame::has_column(const std::string& name) const {
    return name_index_.find(name) != name_index_.end();
}

size_t Frame::column_index(const std::string& name) const {
    auto it = name_index_.find(name);
    if (it == name_index_.end()) {
        throw std::out_of_range("Column not found: " + name);
    }
    return it->second;
}

void Frame::add_column(Column col) {
    if (!row_count_known_) {
        row_count_ = col.size();
        row_count_known_ = true;
    } else {
        validate_column_size(col);
    }
    name_index_[col.name()] = columns_.size();
    columns_.push_back(std::move(col));
}

const std::vector<Column>& Frame::columns() const { return columns_; }

Frame Frame::clone() const {
    std::vector<Column> cloned;
    cloned.reserve(columns_.size());
    for (const auto& col : columns_) {
        cloned.push_back(col.clone());
    }
    return Frame(row_count_, std::move(cloned));
}

void Frame::validate_column_size(const Column& col) const {
    if (col.size() != row_count_) {
        throw std::invalid_argument("Column '" + col.name() + "' has row count " +
                                    std::to_string(col.size()) + "; expected " +
                                    std::to_string(row_count_));
    }
}

Frame Frame::select_columns(const std::vector<std::string>& columns) const {
    std::vector<Column> selected;
    selected.reserve(columns.size());

    for (const auto& name : columns) {
        selected.push_back(column(name).clone());
    }

    return Frame(row_count_, std::move(selected));
}

void Frame::rebuild_index() {
    name_index_.clear();
    for (size_t i = 0; i < columns_.size(); ++i) {
        name_index_[columns_[i].name()] = i;
    }
}

}  // namespace arnio
