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

size_t Column::memory_usage(bool deep) const {
    assert_type_consistency();
    size_t usage = sizeof(Column);
    usage += name_.capacity();
    usage += null_mask_.capacity() / 8;  // approx vector<bool> memory

    if (std::holds_alternative<std::vector<std::string>>(data_)) {
        const auto& vec = std::get<std::vector<std::string>>(data_);
        usage += vec.capacity() * sizeof(std::string);
        if (deep) {
            // deep=True: count exact bytes used by each string's content
            // (s.size()), rather than reserved capacity. This avoids
            // double-counting the SSO buffer already included in sizeof(string)
            // and gives a tighter, accurate byte estimate.
            for (const auto& s : vec) usage += s.size();
        } else {
            // deep=False (default): count each string's reserved capacity,
            // preserving the pre-existing memory_usage() behavior.
            for (const auto& s : vec) usage += s.capacity();
        }
    } else if (std::holds_alternative<std::vector<int64_t>>(data_)) {
        usage += std::get<std::vector<int64_t>>(data_).capacity() * sizeof(int64_t);
    } else if (std::holds_alternative<std::vector<double>>(data_)) {
        usage += std::get<std::vector<double>>(data_).capacity() * sizeof(double);
    } else if (std::holds_alternative<std::vector<bool>>(data_)) {
        usage += std::get<std::vector<bool>>(data_).capacity() / 8;
    }
    return usage;
}

struct PushbackVisitor {
    ColumnData& data;

    void operator()(std::monostate) {
        std::visit(
            [](auto& vec) {
                using T = std::decay_t<decltype(vec)>;
                if constexpr (!std::is_same_v<T, std::monostate>)
                    vec.push_back(typename T::value_type{});
            },
            data);
    }

    void operator()(const std::string& val) {
        std::visit(
            [&val](auto& vec) {
                using T = std::decay_t<decltype(vec)>;

                if constexpr (std::is_same_v<T, std::vector<std::string>>)
                    vec.push_back(val);

                else if constexpr (std::is_same_v<T, std::vector<int64_t>>)
                    vec.push_back(int64_t{});

                else if constexpr (std::is_same_v<T, std::vector<double>>)
                    vec.push_back(double{});

                else if constexpr (std::is_same_v<T, std::vector<bool>>)
                    vec.push_back(false);
            },
            data);
    }

    void operator()(int64_t val) {
        std::visit(
            [val](auto& vec) {
                using T = std::decay_t<decltype(vec)>;

                if constexpr (std::is_same_v<T, std::vector<std::string>>)
                    vec.push_back(std::to_string(val));

                if constexpr (std::is_same_v<T, std::vector<int64_t>>) vec.push_back(val);

                if constexpr (std::is_same_v<T, std::vector<double>>)
                    vec.push_back(static_cast<double>(val));

                if constexpr (std::is_same_v<T, std::vector<bool>>)
                    vec.push_back(val ? true : false);
            },
            data);
    }

    void operator()(double val) {
        std::visit(
            [val](auto& vec) {
                using T = std::decay_t<decltype(vec)>;

                if constexpr (std::is_same_v<T, std::vector<std::string>>)
                    vec.push_back(std::to_string(val));

                if constexpr (std::is_same_v<T, std::vector<int64_t>>)
                    vec.push_back(static_cast<int64_t>(val));

                if constexpr (std::is_same_v<T, std::vector<double>>) vec.push_back(val);

                if constexpr (std::is_same_v<T, std::vector<bool>>)
                    vec.push_back(val ? true : false);
            },
            data);
    }

    void operator()(bool val) {
        std::visit(
            [val](auto& vec) {
                using T = std::decay_t<decltype(vec)>;

                if constexpr (std::is_same_v<T, std::vector<std::string>>)
                    vec.push_back(val ? "true" : "false");

                if constexpr (std::is_same_v<T, std::vector<int64_t>>) vec.push_back(val ? 1 : 0);

                if constexpr (std::is_same_v<T, std::vector<double>>)
                    vec.push_back(val ? 1.0 : 0.0);

                if constexpr (std::is_same_v<T, std::vector<bool>>) vec.push_back(val);
            },
            data);
    }
};

void Column::push_back(const CellValue& value) {
    assert_type_consistency();
    bool is_null_val = std::holds_alternative<std::monostate>(value);

    // Guard: reject non-null insertions into NULL_TYPE columns before
    // mutating any internal state.  NULL_TYPE storage is std::monostate
    // and has no backing vector, so allowing a non-null value would grow
    // null_mask_ without a corresponding data element, leaving the
    // variant storage and null tracking permanently out of sync.
    if (dtype_ == DType::NULL_TYPE && !is_null_val) {
        throw std::invalid_argument("Cannot push non-null value into a NULL_TYPE column");
    }

    null_mask_.push_back(is_null_val);

    PushbackVisitor pv{data_};
    std::visit(pv, value);
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

void Column::reserve(size_t capacity) {
    null_mask_.reserve(capacity);
    std::visit(
        [capacity](auto& vec) {
            using T = std::decay_t<decltype(vec)>;
            if constexpr (!std::is_same_v<T, std::monostate>) {
                vec.reserve(capacity);
            }
        },
        data_);
}

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

Column Column::move_clone() {
    assert_type_consistency();
    return Column(name_, dtype_, std::move(data_), std::move(null_mask_));
}

}  // namespace arnio
