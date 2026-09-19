#include <Arduino.h>
#include <esp_timer.h>
#include <stdint.h>

extern "C" int64_t uxr_millis(void) {
    return esp_timer_get_time() / 1000;
}

extern "C" int64_t uxr_nanos(void) {
    return esp_timer_get_time() * 1000;
}
