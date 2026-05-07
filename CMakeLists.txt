cmake_minimum_required(VERSION 3.15)
project(arnio LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)

find_package(pybind11 CONFIG REQUIRED)

add_subdirectory(cpp)
add_subdirectory(bindings)
