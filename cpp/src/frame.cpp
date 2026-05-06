#include "arnio/frame.h"

#include <stdexcept>

namespace arnio {

Frame::Frame(std::vector<Column> columns) : columns_(std::move(columns)) { rebuild_index(); }

std::pair<size_t, size_t> Frame::shape() const { return {num_rows(), num_cols()}; }

size_t Frame::num_rows() const {
    if (columns_.empty()) return 0;
    return columns_[0].size();
}

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
    return Frame(std::move(cloned));
}

void Frame::rebuild_index() {
    name_index_.clear();
    for (size_t i = 0; i < columns_.size(); ++i) {
        name_index_[columns_[i].name()] = i;
    }
}

}  // namespace arnio
