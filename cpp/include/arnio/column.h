#pragma once

#include "types.h"
#include <vector>
#include <string>
#include <cstddef>

namespace arnio {

class Column {
public:
    Column(const std::string& name, DType dtype);
    Column(const std::string& name, DType dtype, ColumnData data, std::vector<bool> null_mask);

    // Accessors
    const std::string& name() const;
    DType dtype() const;
    size_t size() const;
    bool is_null(size_t idx) const;
    const CellValue at(size_t idx) const;
    size_t memory_usage() const;

    // Mutators (used during construction/loading)
    void push_back(const CellValue& value);
    void push_null();
    void set_name(const std::string& name);
    void set_dtype(DType dtype);

    // Data access
    const ColumnData& data() const;
    const std::vector<bool>& null_mask() const;

    // Clone
    Column clone() const;

private:
    std::string name_;
    DType dtype_;
    ColumnData data_;
    std::vector<bool> null_mask_;  // true = null
};

} // namespace arnio
