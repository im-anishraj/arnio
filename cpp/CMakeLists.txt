include(FetchContent)

FetchContent_Declare(
    Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG        v3.5.3
)
FetchContent_MakeAvailable(Catch2)

add_library(arnio_core STATIC
    src/column.cpp
    src/frame.cpp
    src/csv_reader.cpp
    src/cleaning.cpp
    src/csv_writer.cpp
)
target_include_directories(arnio_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)
target_compile_features(arnio_core PUBLIC cxx_std_17)

macro(arnio_test target source)
    add_executable(${target} ${source})
    target_link_libraries(${target} PRIVATE arnio_core Catch2::Catch2WithMain)
    add_test(NAME ${target} COMMAND $<TARGET_FILE:${target}>)
endmacro()

arnio_test(test_column     tests/test_column.cpp)
arnio_test(test_frame      tests/test_frame.cpp)
arnio_test(test_cleaning   tests/test_cleaning.cpp)
arnio_test(test_csv_parser tests/test_csv_parser.cpp)