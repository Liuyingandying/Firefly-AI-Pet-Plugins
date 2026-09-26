cmake_minimum_required(VERSION 3.14)

project(RVCRealtime VERSION 0.1.0 LANGUAGES C CXX RC)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
option(RVC_BUILD_SMOKE_TEST "Build the standalone worker smoke test" ON)

set(IPLUG_DEPLOY_PLUGINS OFF CACHE BOOL "Keep plugin artifacts inside this project" FORCE)
set(IPLUG2_DIR "${CMAKE_CURRENT_SOURCE_DIR}/third_party/iPlug2" CACHE PATH "iPlug2 root directory")

if(NOT EXISTS "${IPLUG2_DIR}/Dependencies/IPlug/VST3_SDK/base/source/baseiids.cpp"
   OR NOT EXISTS "${IPLUG2_DIR}/Dependencies/IPlug/VST2_SDK/aeffectx.h")
    message(FATAL_ERROR
        "Prepared VST SDK files are missing. Run scripts/prepare-dependencies.ps1 "
        "or use scripts/build.ps1, which runs it automatically.")
endif()

include(${IPLUG2_DIR}/iPlug2.cmake)
find_package(iPlug2 REQUIRED)

iplug_add_plugin(${PROJECT_NAME}
    SOURCES
        src/RVCRealtime.cpp
        src/RVCRealtime.h
        src/WorkerClient.cpp
        src/WorkerClient.hpp
        src/SpscRing.hpp
        src/RvcParameters.hpp
        config.h
        resources/resource.h
        resources/main.rc
    RESOURCES
        resources/fonts/Roboto-Regular.ttf
    FORMATS
        VST2
        VST3
    UI IGRAPHICS
    DEFINES
        UNICODE
        _UNICODE
        NOMINMAX)

if(TARGET RVCRealtime-vst2)
    target_include_directories(RVCRealtime-vst2 BEFORE PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/third_party/vst2-compat"
        "${CMAKE_CURRENT_SOURCE_DIR}/third_party/vst2sdk/include")
endif()

if(MSVC)
    foreach(target RVCRealtime-vst2 RVCRealtime-vst3)
        if(TARGET ${target})
            target_compile_options(${target} PRIVATE /W4 /permissive- /utf-8)
        endif()
    endforeach()
endif()

if(RVC_BUILD_SMOKE_TEST)
    add_executable(rvc-worker-smoke
        tools/worker_smoke.cpp
        src/WorkerClient.cpp
        src/WorkerClient.hpp
        src/SpscRing.hpp
        src/RvcParameters.hpp
        config.h)
    target_include_directories(rvc-worker-smoke PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}"
        "${CMAKE_CURRENT_SOURCE_DIR}/src")
    target_compile_definitions(rvc-worker-smoke PRIVATE
        UNICODE
        _UNICODE
        NOMINMAX)
    if(MSVC)
        target_compile_options(rvc-worker-smoke PRIVATE /W4 /permissive- /utf-8)
    endif()
    add_custom_command(TARGET rvc-worker-smoke POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory
            "$<TARGET_FILE_DIR:rvc-worker-smoke>/RVCRealtime.resources/worker"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${CMAKE_CURRENT_SOURCE_DIR}/worker/rvc_worker.py"
            "$<TARGET_FILE_DIR:rvc-worker-smoke>/RVCRealtime.resources/worker/rvc_worker.py")

    add_executable(rvc-vst2-smoke tools/vst2_smoke.cpp)
    target_include_directories(rvc-vst2-smoke PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/third_party/vst2-compat"
        "${CMAKE_CURRENT_SOURCE_DIR}/third_party/vst2sdk/include")
    target_compile_definitions(rvc-vst2-smoke PRIVATE
        UNICODE
        _UNICODE
        NOMINMAX)
    if(MSVC)
        target_compile_options(rvc-vst2-smoke PRIVATE /W4 /permissive- /utf-8)
    endif()
endif()
