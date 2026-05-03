#pragma once

#include <cstdint>
#include <string>
#include <variant>
#include <vector>

namespace arnio {

enum class DType {
    STRING,
    INT64,
    FLOAT64,
    BOOL,
    NULL_TYPE
};

using CellValue = std::variant<std::monostate, std::string, int64_t, double, bool>;

using ColumnData = std::variant<
    std::monostate,
    std::vector<std::string>,
    std::vector<int64_t>,
    std::vector<double>,
    std::vector<bool>
>;

inline std::string dtype_to_string(DType dt) {
    switch (dt) {
        case DType::STRING:    return "string";
        case DType::INT64:     return "int64";
        case DType::FLOAT64:   return "float64";
        case DType::BOOL:      return "bool";
        case DType::NULL_TYPE: return "null";
        default:               return "unknown";
    }
}

inline DType string_to_dtype(const std::string& s) {
    if (s == "string")  return DType::STRING;
    if (s == "int64")   return DType::INT64;
    if (s == "float64") return DType::FLOAT64;
    if (s == "bool")    return DType::BOOL;
    return DType::NULL_TYPE;
}

} // namespace arnio
