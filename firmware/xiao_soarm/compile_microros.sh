#!/bin/bash
# Direct compilation of micro-ROS source files for ESP32-C3 (riscv32)
# Uses PlatformIO toolchain, bypasses colcon/CMake
set -e

TC=~/.platformio/packages/toolchain-riscv32-esp
IDF=~/.platformio/packages/framework-arduinoespressif32/tools/sdk/esp32c3
CC=$TC/bin/riscv32-esp-elf-gcc
CXX=$TC/bin/riscv32-esp-elf-g++
AR=$TC/bin/riscv32-esp-elf-ar
MCU_WS=/tmp/firmware/mcu_ws
BUILD=/tmp/firmware/obj_esp32c3
OUT=$BUILD/libmicroros.a

rm -rf $BUILD
mkdir -p $BUILD

CFLAGS="-c -march=rv32imc -mabi=ilp32 -Os -ffunction-sections -fdata-sections"
CFLAGS="$CFLAGS -D__ESP32C3__ -DESP_PLATFORM -D__FreeRTOS__"
CFLAGS="$CFLAGS -I$IDF/include/freertos/include"
CFLAGS="$CFLAGS -I$IDF/include/freertos/include/freertos"
CFLAGS="$CFLAGS -I$IDF/include"
CFLAGS="$CFLAGS -I$IDF/include/config"
CFLAGS="$CFLAGS -I$IDF/include/hal/include"
CFLAGS="$CFLAGS -I$IDF/include/soc/include"
CFLAGS="$CFLAGS -I$TC/riscv32-esp-elf/include"
CFLAGS="$CFLAGS -DRMW_UXRCE_TRANSPORT=custom"
CFLAGS="$CFLAGS -DUCLIENT_PROFILE_CUSTOM_TRANSPORT=ON"
CFLAGS="$CFLAGS -DRCUTILS_NO_FILESYSTEM=ON"
CFLAGS="$CFLAGS -DRCUTILS_NO_THREAD_SUPPORT=ON"
CFLAGS="$CFLAGS -DRCUTILS_NO_64_ATOMIC=ON"
CFLAGS="$CFLAGS -DMICRO_ROS_ARDUINO"

# Include paths for each micro-ROS package
I_MICROCDR="$MCU_WS/eProsima/Micro-CDR/include"
I_CLIENT="$MCU_WS/eProsima/Micro-XRCE-DDS-Client/include"
I_RMW_UXRCE="$MCU_WS/uros/rmw_microxrcedds/rmw_microxrcedds/include"
I_RCL="$MCU_WS/uros/rcl/rcl/include"
I_RCLC="$MCU_WS/uros/rclc/rclc/include"
I_RCUTILS="$MCU_WS/ros2/rcutils/include"
I_RMW="$MCU_WS/ros2/rmw/rmw/include"
I_ROSIDL_C="$MCU_WS/ros2/rosidl/rosidl_runtime_c/include"
I_ROSIDL_TSC="$MCU_WS/uros/rosidl_typesupport_microxrcedds/rosidl_typesupport_microxrcedds_c/include"
I_STD_MSGS="$MCU_WS/ros2/common_interfaces/std_msgs/include"
I_SENSOR_MSGS="$MCU_WS/ros2/common_interfaces/sensor_msgs/include"
I_BUILTIN="$MCU_WS/ros2/rcl_interfaces/builtin_interfaces/include"

ALL_INC="-I$I_MICROCDR -I$I_CLIENT -I$I_RMW_UXRCE -I$I_RCL -I$I_RCLC"
ALL_INC="$ALL_INC -I$I_RCUTILS -I$I_RMW -I$I_ROSIDL_C -I$I_ROSIDL_TSC"
ALL_INC="$ALL_INC -I$I_STD_MSGS -I$I_SENSOR_MSGS -I$I_BUILTIN"

compile_dir() {
    local dir=$1
    local pattern=$2
    local lang=$3
    local extra_inc=$4
    local comp=$([ "$lang" == "cpp" ] && echo "$CXX" || echo "$CC")
    local cflags="$CFLAGS"
    [ "$lang" == "cpp" ] && cflags="$cflags -fno-rtti -fno-exceptions"

    for f in $(find $dir -name "$pattern" -type f 2>/dev/null | grep -v test | grep -v example | head -50); do
        local obj="$BUILD/$(basename $f .${lang}).o"
        echo "  CC $(basename $f)"
        $comp $cflags $ALL_INC $extra_inc -o $obj $f 2>/dev/null && echo "$obj" >> $BUILD/objs.txt || true
    done
}

echo "=== Compiling micro-ROS for ESP32-C3 (riscv32) ==="

echo "--- rcutils ---"
compile_dir "$MCU_WS/ros2/rcutils/src" "*.c" "c" ""

echo "--- micro-CDR ---"
compile_dir "$MCU_WS/eProsima/Micro-CDR/src/c" "*.c" "c" ""

echo "--- microxrcedds_client ---"
compile_dir "$MCU_WS/eProsima/Micro-XRCE-DDS-Client/src/c" "*.c" "c" ""
compile_dir "$MCU_WS/eProsima/Micro-XRCE-DDS-Client/src/c/profile/transport/custom" "*.c" "c" ""

echo "--- rmw_microxrcedds ---"
compile_dir "$MCU_WS/uros/rmw_microxrcedds/rmw_microxrcedds/src" "*.c" "c" ""

echo "--- rcl ---"
compile_dir "$MCU_WS/uros/rcl/rcl/src" "*.c" "c" ""

echo "--- rclc ---"
compile_dir "$MCU_WS/uros/rclc/rclc/src" "*.c" "c" ""

echo "--- rosidl_runtime_c ---"
compile_dir "$MCU_WS/ros2/rosidl/rosidl_runtime_c/src" "*.c" "c" ""

echo "=== Linking libmicroros.a ==="
OBJS=$(cat $BUILD/objs.txt 2>/dev/null | tr '\n' ' ')
echo "Objects: $(echo $OBJS | wc -w) files"
$AR rcs $OUT $OBJS 2>&1 || true
echo "Done: $OUT"
ls -lh $OUT