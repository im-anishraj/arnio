add_library(arnio_core STATIC
    src/column.cpp
    src/frame.cpp
    src/csv_reader.cpp
    src/cleaning.cpp
)

target_include_directories(arnio_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_features(arnio_core PUBLIC cxx_std_17)

add_executable(test_column_consistency
    tests/test_column_consistency.cpp
)
target_link_libraries(test_column_consistency PRIVATE arnio_core)
