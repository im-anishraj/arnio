#include "arnio/column.h"

#include <stdexcept>
#include <utility>

namespace arnio {

Column::Column(const std::string& name, DType dtype) : name_(name), dtype_(dtype) {
    switch (dtype) {
        case DType::STRING:
            data_ = std::vector<std::string>{};
            break;
        case DType::INT64:
            data_ = std::vector<int64_t>{};
            break;
        case DType::FLOAT64:
            data_ = std::vector<double>{};
            break;
        case DType::BOOL:
            data_ = std::vector<bool>{};
            break;
        case DType::NULL_TYPE:
            data_ = std::monostate{};
            break;
    }
}

Column::Column(const std::string& name, DType dtype, ColumnData data, std::vector<bool> null_mask)
    : name_(name), dtype_(dtype), data_(std::move(data)), null_mask_(std::move(null_mask)) {}

const std::string& Column::name() const { return name_; }
DType Column::dtype() const { return dtype_; }
size_t Column::size() const { return null_mask_.size(); }

bool Column::is_null(size_t idx) const {
    if (idx >= null_mask_.size()) {
        throw std::out_of_range("Column index out of range");
    }
    return null_mask_[idx];
}

const CellValue Column::at(size_t idx) const {
    assert_type_consistency();
    if (idx >= null_mask_.size()) {
        throw std::out_of_range("Column index out of range");
    }
    if (null_mask_[idx]) return std::monostate{};

    if (std::holds_alternative<std::vector<std::string>>(data_)) {
        return std::get<std::vector<std::string>>(data_)[idx];
    } else if (std::holds_alternative<std::vector<int64_t>>(data_)) {
        return std::get<std::vector<int64_t>>(data_)[idx];
    } else if (std::holds_alternative<std::vector<double>>(data_)) {
        return std::get<std::vector<double>>(data_)[idx];
    } else if (std::holds_alternative<std::vector<bool>>(data_)) {
        return static_cast<bool>(std::get<std::vector<bool>>(data_)[idx]);
    }
    return std::monostate{};
}

size_t Column::memory_usage() const {
    assert_type_consistency();
    size_t usage = sizeof(Column);
    usage += name_.capacity();
    usage += null_mask_.capacity() / 8;  // approx vector<bool> memory

    if (std::holds_alternative<std::vector<std::string>>(data_)) {
        const auto& vec = std::get<std::vector<std::string>>(data_);
        usage += vec.capacity() * sizeof(std::string);
        for (const auto& s : vec) usage += s.capacity();
    } else if (std::holds_alternative<std::vector<int64_t>>(data_)) {
        usage += std::get<std::vector<int64_t>>(data_).capacity() * sizeof(int64_t);
    } else if (std::holds_alternative<std::vector<double>>(data_)) {
        usage += std::get<std::vector<double>>(data_).capacity() * sizeof(double);
    } else if (std::holds_alternative<std::vector<bool>>(data_)) {
        usage += std::get<std::vector<bool>>(data_).capacity() / 8;
    }
    return usage;
}

void Column::push_back(const CellValue& value) {
    assert_type_consistency();
    bool is_null_val = std::holds_alternative<std::monostate>(value);
    null_mask_.push_back(is_null_val);

    if (std::holds_alternative<std::vector<std::string>>(data_)) {
        auto& vec = std::get<std::vector<std::string>>(data_);
        if (std::holds_alternative<std::string>(value))
            vec.push_back(std::get<std::string>(value));
        else if (std::holds_alternative<int64_t>(value))
            vec.push_back(std::to_string(std::get<int64_t>(value)));
        else if (std::holds_alternative<double>(value))
            vec.push_back(std::to_string(std::get<double>(value)));
        else if (std::holds_alternative<bool>(value))
            vec.push_back(std::get<bool>(value) ? "true" : "false");
        else
            vec.push_back("");
    } else if (std::holds_alternative<std::vector<int64_t>>(data_)) {
        auto& vec = std::get<std::vector<int64_t>>(data_);
        if (std::holds_alternative<int64_t>(value))
            vec.push_back(std::get<int64_t>(value));
        else if (std::holds_alternative<bool>(value))
            vec.push_back(std::get<bool>(value) ? 1 : 0);
        else if (std::holds_alternative<double>(value))
            vec.push_back(static_cast<int64_t>(std::get<double>(value)));
        else
            vec.push_back(0);
    } else if (std::holds_alternative<std::vector<double>>(data_)) {
        auto& vec = std::get<std::vector<double>>(data_);
        if (std::holds_alternative<double>(value))
            vec.push_back(std::get<double>(value));
        else if (std::holds_alternative<int64_t>(value))
            vec.push_back(static_cast<double>(std::get<int64_t>(value)));
        else if (std::holds_alternative<bool>(value))
            vec.push_back(std::get<bool>(value) ? 1.0 : 0.0);
        else
            vec.push_back(0.0);
    } else if (std::holds_alternative<std::vector<bool>>(data_)) {
        auto& vec = std::get<std::vector<bool>>(data_);
        if (std::holds_alternative<bool>(value))
            vec.push_back(std::get<bool>(value));
        else if (std::holds_alternative<int64_t>(value))
            vec.push_back(std::get<int64_t>(value) != 0);
        else if (std::holds_alternative<double>(value))
            vec.push_back(std::get<double>(value) != 0.0);
        else
            vec.push_back(false);
    }
}

void Column::push_null() {
    assert_type_consistency();
    null_mask_.push_back(true);
    if (std::holds_alternative<std::vector<std::string>>(data_)) {
        std::get<std::vector<std::string>>(data_).push_back("");
    } else if (std::holds_alternative<std::vector<int64_t>>(data_)) {
        std::get<std::vector<int64_t>>(data_).push_back(0);
    } else if (std::holds_alternative<std::vector<double>>(data_)) {
        std::get<std::vector<double>>(data_).push_back(0.0);
    } else if (std::holds_alternative<std::vector<bool>>(data_)) {
        std::get<std::vector<bool>>(data_).push_back(false);
    }
}

void Column::set_name(const std::string& name) { name_ = name; }
void Column::set_dtype(DType dtype) { dtype_ = dtype; }

void Column::assert_type_consistency() const {
    bool consistent = false;
    switch (dtype_) {
        case DType::STRING:
            consistent = std::holds_alternative<std::vector<std::string>>(data_);
            break;
        case DType::INT64:
            consistent = std::holds_alternative<std::vector<int64_t>>(data_);
            break;
        case DType::FLOAT64:
            consistent = std::holds_alternative<std::vector<double>>(data_);
            break;
        case DType::BOOL:
            consistent = std::holds_alternative<std::vector<bool>>(data_);
            break;
        case DType::NULL_TYPE:
            consistent = std::holds_alternative<std::monostate>(data_);
            break;
    }
    if (!consistent) {
        throw std::logic_error("Column type inconsistency: dtype does not match data variant");
    }
}

const ColumnData& Column::data() const {
    assert_type_consistency();
    return data_;
}
const std::vector<bool>& Column::null_mask() const { return null_mask_; }

Column Column::clone() const {
    assert_type_consistency();
    return Column(name_, dtype_, data_, null_mask_);
}

}  // namespace arnio
