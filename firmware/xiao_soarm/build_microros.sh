#!/bin/bash
# Build micro-ROS library for ESP32-C3 (riscv32)
# Uses PlatformIO's ESP-IDF toolchain

set -e

PIO_PACKAGES=~/.platformio/packages
TOOLCHAIN=$PIO_PACKAGES/toolchain-riscv32-esp
IDF_PATH=$PIO_PACKAGES/framework-arduinoespressif32/tools/sdk/esp32c3
TARGET=riscv32-esp-elf
MCU_WS=/tmp/firmware/mcu_ws
BUILD_DIR=/tmp/firmware/build_esp32c3
INSTALL_DIR=$BUILD_DIR/install

export PATH=$TOOLCHAIN/bin:$PATH
export CC=$TARGET-gcc
export CXX=$TARGET-g++
export AR=$TARGET-ar
export LD=$TARGET-ld
export OBJCOPY=$TARGET-objcopy
export STRIP=$TARGET-strip

# FreeRTOS + IDF compile flags
FREERTOS_INC="$IDF_PATH/include/freertos/include"
LWIP_INC="$IDF_PATH/include/lwip/include"
HAL_INC="$IDF_PATH/include/hal/include"
SOC_INC="$IDF_PATH/include/soc/include"
NEWLIB_INC="$TOOLCHAIN/riscv32-esp-elf/include"
CONFIG_INC="$IDF_PATH/include/config"

CFLAGS="-march=rv32imc -mabi=ilp32 -Os -ffunction-sections -fdata-sections"
CFLAGS="$CFLAGS -D__ESP32C3__ -DESP_PLATFORM"
CFLAGS="$CFLAGS -I$FREERTOS_INC -I$IDF_PATH/include -I$CONFIG_INC"
CFLAGS="$CFLAGS -I$HAL_INC -I$SOC_INC -I$NEWLIB_INC"

CXXFLAGS="$CFLAGS -fno-rtti -fno-exceptions"

# Use colcon - need ROS2 and dev_ws for build tools (ament_cmake, etc.)
source /opt/ros/humble/setup.bash
source /tmp/firmware/dev_ws/install/setup.bash 2>/dev/null || true

cd $MCU_WS

# We only need the client libs, skip tests and examples
colcon build \
    --merge-install \
    --install-base $INSTALL_DIR \
    --cmake-args \
        -DCMAKE_SYSTEM_NAME=Generic \
        -DCMAKE_SYSTEM_PROCESSOR=riscv32 \
        -DCMAKE_C_COMPILER=$CC \
        -DCMAKE_CXX_COMPILER=$CXX \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER \
        -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY \
        -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY \
        -DCMAKE_PREFIX_PATH="$INSTALL_DIR;/opt/ros/humble" \
        -DCMAKE_INSTALL_PREFIX=$INSTALL_DIR \
        -DBUILD_TESTING=OFF \
        -DRCUTILS_NO_FILESYSTEM=ON \
        -DRCUTILS_NO_THREAD_SUPPORT=ON \
        -DUCLIENT_PROFILE_CUSTOM_TRANSPORT=ON \
        -DUCLIENT_PROFILE_UDP=OFF \
        -DUCLIENT_PROFILE_SERIAL=OFF \
        -DUCLIENT_PROFILE_TCP=OFF \
        -DRMW_UXRCE_TRANSPORT=custom \
    --continue-on-error \
    --packages-up-to \
        rmw_microxrcedds rclc sensor_msgs std_msgs geometry_msgs \
    --metas colcon.meta 2>&1 | tail -50

echo "=== Done ==="
echo "Libraries in: $INSTALL_DIR/lib/"
find $INSTALL_DIR -name "*.a" 2>/dev/null
