#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "arnio/cleaning.h"
#include "arnio/column.h"
#include "arnio/csv_reader.h"
#include "arnio/frame.h"
#include "arnio/types.h"

namespace py = pybind11;
using namespace arnio;

PYBIND11_MODULE(_arnio_cpp, m) {
    m.doc() = "arnio C++ backend";

    // --- DType enum ---
    py::enum_<DType>(m, "DType")
        .value("STRING", DType::STRING)
        .value("INT64", DType::INT64)
        .value("FLOAT64", DType::FLOAT64)
        .value("BOOL", DType::BOOL)
        .value("NULL_TYPE", DType::NULL_TYPE)
        .export_values();

    // --- Column --
    py::class_<Column>(m, "Column")
        .def(py::init<const std::string&, DType>(), py::arg("name"), py::arg("dtype"))
        .def("name", &Column::name)
        .def("dtype", &Column::dtype)
        .def("size", &Column::size)
        .def("is_null", &Column::is_null)
        .def("memory_usage", &Column::memory_usage)
        .def("push_null", &Column::push_null)
        .def("push_back",
             [](Column& col, py::object value) {
                 if (value.is_none()) {
                     col.push_null();
                 } else if (py::isinstance<py::bool_>(value)) {
                     col.push_back(value.cast<bool>());
                 } else if (py::isinstance<py::int_>(value)) {
                     col.push_back(value.cast<int64_t>());
                 } else if (py::isinstance<py::float_>(value)) {
                     col.push_back(value.cast<double>());
                 } else {
                     col.push_back(value.cast<std::string>());
                 }
             })
        .def("at",
             [](const Column& col, size_t idx) -> py::object {
                 if (col.is_null(idx)) return py::none();
                 auto val = col.at(idx);
                 if (std::holds_alternative<std::string>(val))
                     return py::cast(std::get<std::string>(val));
                 if (std::holds_alternative<int64_t>(val)) return py::cast(std::get<int64_t>(val));
                 if (std::holds_alternative<double>(val)) return py::cast(std::get<double>(val));
                 if (std::holds_alternative<bool>(val)) return py::cast(std::get<bool>(val));
                 return py::none();
             })
        .def("to_numpy_float",
             [](py::object col_obj) {
                 const Column& col = col_obj.cast<const Column&>();
                 if (col.dtype() != DType::FLOAT64)
                     throw std::runtime_error("Not a FLOAT64 column");
                 const auto& vec = std::get<std::vector<double>>(col.data());
                 return py::array_t<double>({vec.size()}, {sizeof(double)}, vec.data(), col_obj);
             })
        .def("to_numpy_int",
             [](py::object col_obj) {
                 const Column& col = col_obj.cast<const Column&>();
                 if (col.dtype() != DType::INT64) throw std::runtime_error("Not an INT64 column");
                 const auto& vec = std::get<std::vector<int64_t>>(col.data());
                 return py::array_t<int64_t>({vec.size()}, {sizeof(int64_t)}, vec.data(), col_obj);
             })
        .def("to_numpy_bool",
             [](py::object col_obj) {
                 const Column& col = col_obj.cast<const Column&>();
                 if (col.dtype() != DType::BOOL) throw std::runtime_error("Not a BOOL column");
                 const auto& vec = std::get<std::vector<bool>>(col.data());
                 auto result = py::array_t<bool>(vec.size());
                 auto ptr = result.mutable_data();
                 for (size_t i = 0; i < vec.size(); ++i) ptr[i] = static_cast<bool>(vec[i]);
                 return result;
             })
        .def("to_python_list",
             [](const Column& col) {
                 py::list result;
                 if (col.dtype() == DType::STRING) {
                     const auto& vec = std::get<std::vector<std::string>>(col.data());
                     for (size_t i = 0; i < vec.size(); ++i) {
                         if (col.is_null(i)) {
                             result.append(py::none());
                         } else {
                             result.append(py::str(vec[i]));
                         }
                     }
                 } else if (col.dtype() == DType::BOOL) {
                     const auto& vec = std::get<std::vector<bool>>(col.data());
                     for (size_t i = 0; i < vec.size(); ++i) {
                         if (col.is_null(i)) {
                             result.append(py::none());
                         } else {
                             result.append(py::bool_(static_cast<bool>(vec[i])));
                         }
                     }
                 } else if (col.dtype() == DType::INT64) {
                     const auto& vec = std::get<std::vector<int64_t>>(col.data());
                     for (size_t i = 0; i < vec.size(); ++i) {
                         if (col.is_null(i)) {
                             result.append(py::none());
                         } else {
                             result.append(py::int_(vec[i]));
                         }
                     }
                 } else if (col.dtype() == DType::FLOAT64) {
                     const auto& vec = std::get<std::vector<double>>(col.data());
                     for (size_t i = 0; i < vec.size(); ++i) {
                         if (col.is_null(i)) {
                             result.append(py::none());
                         } else {
                             result.append(py::float_(vec[i]));
                         }
                     }
                 } else {
                     for (size_t i = 0; i < col.size(); ++i) result.append(py::none());
                 }
                 return result;
             })
        .def("get_null_mask", [](const Column& col) {
            const auto& mask = col.null_mask();
            auto result = py::array_t<bool>(mask.size());
            auto ptr = result.mutable_data();
            for (size_t i = 0; i < mask.size(); ++i) ptr[i] = static_cast<bool>(mask[i]);
            return result;
        });

    // --- Frame ---
    py::class_<Frame>(m, "Frame")
        .def(py::init<>())
        .def("shape", &Frame::shape)
        .def("num_rows", &Frame::num_rows)
        .def("num_cols", &Frame::num_cols)
        .def("column_names", &Frame::column_names)
        .def("dtypes", &Frame::dtypes)
        .def("memory_usage", &Frame::memory_usage)
        .def("has_column", &Frame::has_column)
        .def(
            "column_by_index",
            [](const Frame& f, size_t idx) -> const Column& { return f.column(idx); },
            py::return_value_policy::reference_internal)
        .def(
            "column_by_name",
            [](const Frame& f, const std::string& name) -> const Column& { return f.column(name); },
            py::return_value_policy::reference_internal)
        .def("add_column", &Frame::add_column)
        .def("clone", &Frame::clone)
        .def_static("from_dict", [](py::dict cols_dict) {
            Frame frame;
            for (auto item : cols_dict) {
                std::string name = py::cast<std::string>(item.first);
                py::list values = py::cast<py::list>(item.second);

                DType dtype = DType::STRING;
                for (auto val : values) {
                    if (val.is_none()) continue;
                    if (py::isinstance<py::bool_>(val)) {
                        dtype = DType::BOOL;
                        break;
                    }
                    if (py::isinstance<py::int_>(val)) {
                        dtype = DType::INT64;
                        break;
                    }
                    if (py::isinstance<py::float_>(val)) {
                        dtype = DType::FLOAT64;
                        break;
                    }
                    break;
                }

                Column col(name, dtype);
                for (auto val : values) {
                    if (val.is_none()) {
                        col.push_null();
                        continue;
                    }
                    if (dtype == DType::BOOL)
                        col.push_back(val.cast<bool>());
                    else if (dtype == DType::INT64)
                        col.push_back(val.cast<int64_t>());
                    else if (dtype == DType::FLOAT64)
                        col.push_back(val.cast<double>());
                    else
                        col.push_back(py::str(val).cast<std::string>());
                }
                frame.add_column(col);
            }
            return frame;
        });

    // --- CsvReader ---
    py::class_<CsvConfig>(m, "CsvConfig")
        .def(py::init<>())
        .def_readwrite("delimiter", &CsvConfig::delimiter)
        .def_readwrite("has_header", &CsvConfig::has_header)
        .def_readwrite("usecols", &CsvConfig::usecols)
        .def_readwrite("nrows", &CsvConfig::nrows)
        .def_readwrite("encoding", &CsvConfig::encoding);

    py::class_<CsvReader>(m, "CsvReader")
        .def(py::init<const CsvConfig&>(), py::arg("config") = CsvConfig{})
        .def("read", &CsvReader::read)
        .def("scan_schema", &CsvReader::scan_schema);

    // --- Cleaning functions ---
    m.def("drop_nulls", &drop_nulls, py::arg("frame"), py::arg("subset") = std::nullopt);

    m.def(
        "fill_nulls",
        [](const Frame& frame, py::object value,
           const std::optional<std::vector<std::string>>& subset) {
            CellValue cv;
            if (py::isinstance<py::str>(value)) {
                cv = value.cast<std::string>();
            } else if (py::isinstance<py::bool_>(value)) {
                cv = value.cast<bool>();
            } else if (py::isinstance<py::int_>(value)) {
                cv = value.cast<int64_t>();
            } else if (py::isinstance<py::float_>(value)) {
                cv = value.cast<double>();
            } else {
                cv = std::monostate{};
            }
            return fill_nulls(frame, cv, subset);
        },
        py::arg("frame"), py::arg("value"), py::arg("subset") = std::nullopt);

    m.def("drop_duplicates", &drop_duplicates, py::arg("frame"), py::arg("subset") = std::nullopt,
          py::arg("keep") = "first");

    m.def("strip_whitespace", &strip_whitespace, py::arg("frame"),
          py::arg("subset") = std::nullopt);

    m.def("normalize_case", &normalize_case, py::arg("frame"), py::arg("subset") = std::nullopt,
          py::arg("case_type") = "lower");

    m.def("rename_columns", &rename_columns, py::arg("frame"), py::arg("mapping"));

    m.def("cast_types", &cast_types, py::arg("frame"), py::arg("mapping"));
}
