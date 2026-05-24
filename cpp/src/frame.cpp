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

Column& Frame::column_mut(size_t idx) {
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
    if (name_index_.find(col.name()) != name_index_.end()) {
        throw std::invalid_argument("Column '" + col.name() +
                                    "' already exists in Frame. Drop or rename it before adding.");
    }
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

std::vector<std::pair<std::string, std::vector<std::pair<std::string, double>>>> Frame::describe()
    const {
    std::vector<std::pair<std::string, std::vector<std::pair<std::string, double>>>> summary;

    for (const auto& col : columns_) {
        std::string col_name = col.name();
        std::vector<std::pair<std::string, double>> stats;

        size_t total_rows = col.size();
        size_t null_count = 0;
        size_t valid_count = 0;
        std::string type_str = dtype_to_string(col.dtype());

        if (type_str == "int64" || type_str == "float64") {
            double sum = 0.0;
            double min_val = std::numeric_limits<double>::infinity();
            double max_val = -std::numeric_limits<double>::infinity();

            for (size_t i = 0; i < total_rows; ++i) {
                if (col.is_null(i)) {
                    null_count++;
                    continue;
                }
                valid_count++;

                double val = 0.0;
                if (col.dtype() == DType::INT64) {
                    val = static_cast<double>(std::get<int64_t>(col.at(i)));
                } else {
                    val = std::get<double>(col.at(i));
                }

                sum += val;
                if (val < min_val) min_val = val;
                if (val > max_val) max_val = val;
            }

            // Push metrics in the exact forward order requested by the maintainer
            stats.push_back({"count", static_cast<double>(valid_count)});
            stats.push_back({"nulls", static_cast<double>(null_count)});
            if (valid_count > 0) {
                stats.push_back({"mean", sum / valid_count});
                stats.push_back({"min", min_val});
                stats.push_back({"max", max_val});
            } else {
                stats.push_back({"mean", 0.0});
                stats.push_back({"min", 0.0});
                stats.push_back({"max", 0.0});
            }

            summary.push_back({col_name, stats});
        } else if (type_str == "string") {
            std::unordered_set<std::string> unique_values;

            for (size_t i = 0; i < total_rows; ++i) {
                if (col.is_null(i)) {
                    null_count++;
                    continue;
                }
                valid_count++;
                unique_values.insert(std::get<std::string>(col.at(i)));
            }

            stats.push_back({"count", static_cast<double>(valid_count)});
            stats.push_back({"nulls", static_cast<double>(null_count)});
            stats.push_back({"unique", static_cast<double>(unique_values.size())});

            summary.push_back({col_name, stats});
        }
    }

    return summary;
}

Frame concat(const std::vector<Frame>& frames) {
    if (frames.empty()) {
        throw std::invalid_argument("Cannot concatenate an empty list of Frames");
    }
    if (frames.size() == 1) {
        return frames[0].clone();
    }

    const Frame& first = frames[0];
    size_t num_cols = first.num_cols();
    std::vector<std::string> target_names = first.column_names();
    std::vector<DType> target_dtypes;
    target_dtypes.reserve(num_cols);
    for (size_t c = 0; c < num_cols; ++c) {
        target_dtypes.push_back(first.column(c).dtype());
    }

    // Validate subsequent frames
    for (size_t i = 1; i < frames.size(); ++i) {
        const Frame& f = frames[i];
        if (f.num_cols() != num_cols) {
            throw std::invalid_argument("Column count mismatch in concat");
        }
        for (size_t c = 0; c < num_cols; ++c) {
            const Column& col = f.column(c);
            if (col.name() != target_names[c]) {
                throw std::invalid_argument("Column name or order mismatch in concat: expected '" +
                                            target_names[c] + "', got '" + col.name() + "'");
            }
            if (col.dtype() != target_dtypes[c]) {
                throw std::invalid_argument("Column dtype mismatch in concat");
            }
        }
    }

    // Create cloned columns from the first frame
    std::vector<Column> concat_cols;
    concat_cols.reserve(num_cols);
    for (size_t c = 0; c < num_cols; ++c) {
        concat_cols.push_back(first.column(c).clone());
    }

    // Append columns from subsequent frames
    for (size_t i = 1; i < frames.size(); ++i) {
        const Frame& f = frames[i];
        for (size_t c = 0; c < num_cols; ++c) {
            concat_cols[c].append(f.column(c));
        }
    }

    // Calculate total rows
    size_t total_rows = 0;
    for (const auto& f : frames) {
        total_rows += f.num_rows();
    }

    return Frame(total_rows, std::move(concat_cols));
}

}  // namespace arnio
