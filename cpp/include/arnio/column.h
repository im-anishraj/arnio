#pragma once

#include <cstddef>
#include <string>
#include <vector>

#include "types.h"

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
    size_t memory_usage(bool deep = false) const;

    // Mutators (used during construction/loading)
    void push_back(const CellValue& value);
    void push_null();
    void set_name(const std::string& name);

    // Data access
    const ColumnData& data() const;
    const std::vector<bool>& null_mask() const;

    // Clone
    Column clone() const;

    // Move-clone: transfers ownership of internal data to a new Column.
    // The source Column is left in a valid but empty state.
    // Use only when the source will not be accessed again (e.g. when
    // building a new Frame from a Frame that is about to be discarded).
    Column move_clone();

   private:
    void set_dtype(DType dtype);
    void assert_type_consistency() const;

    std::string name_;
    DType dtype_;
    ColumnData data_;
    std::vector<bool> null_mask_;  // true = null
};

}  // namespace arnio
