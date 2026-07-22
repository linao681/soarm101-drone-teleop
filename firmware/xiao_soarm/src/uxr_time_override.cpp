#include <Arduino.h>
#include <esp_timer.h>
#include <stdint.h>

// Micro XRCE-DDS uses these functions for session and heartbeat deadlines.
// Use ESP-IDF's monotonic 64-bit timer instead of CLOCK_REALTIME so network
// changes and wall-clock synchronization cannot make deadline deltas negative.
extern "C" int64_t uxr_millis(void)
{
    return esp_timer_get_time() / 1000;
}

extern "C" int64_t uxr_nanos(void)
{
    return esp_timer_get_time() * 1000;
}
