#if defined(ESP32) || defined(TARGET_PORTENTA_H7_M7) || defined(ARDUINO_GIGA) || defined(ARDUINO_NANO_RP2040_CONNECT) || defined(ARDUINO_WIO_TERMINAL) || defined(BOARD_WITH_ESP_AT) || defined(ARDUINO_UNOR4_WIFI) || defined(ARDUINO_OPTA)
#include <Arduino.h>


#if defined(ESP32) || defined(TARGET_PORTENTA_H7_M7) || defined(ARDUINO_GIGA) || defined(ARDUINO_OPTA)
#include <WiFi.h>
#include <WiFiUdp.h>
#elif defined(ARDUINO_NANO_RP2040_CONNECT)
#include <SPI.h>
#include <WiFiNINA.h>
#elif defined(ARDUINO_WIO_TERMINAL)
#include <rpcWiFi.h>
#include <WiFiUdp.h>
#elif defined(BOARD_WITH_ESP_AT)
#include <WiFiEspAT.h>
#elif defined(ARDUINO_UNOR4_WIFI)
#include <WiFiS3.h>
#endif

#include <micro_ros_arduino.h>
#include <lwip/sockets.h>
#include <errno.h>

extern "C"
{

  static int udp_socket = -1;
  static struct sockaddr_in agent_address;

  struct udp_trace_entry {
    char operation;
    int requested;
    int timeout;
    int result;
    int status;
  };

  static struct udp_trace_entry udp_trace[64];
  static size_t udp_trace_count = 0;

  static void record_udp_trace(char operation, int requested, int timeout,
                               int result, int status)
  {
    if (udp_trace_count < sizeof(udp_trace) / sizeof(udp_trace[0])) {
      udp_trace[udp_trace_count++] = {
        operation, requested, timeout, result, status
      };
    }
  }

  void arduino_wifi_transport_dump_trace()
  {
    Serial.printf("UDP trace entries: %u\n", (unsigned) udp_trace_count);
    for (size_t i = 0; i < udp_trace_count; ++i) {
      const struct udp_trace_entry &entry = udp_trace[i];
      Serial.printf("  %u %c req=%d timeout=%d result=%d status=%d\n",
                    (unsigned) i, entry.operation, entry.requested,
                    entry.timeout, entry.result, entry.status);
    }
    udp_trace_count = 0;
  }

  bool arduino_wifi_transport_open(struct uxrCustomTransport * transport)
  {
    struct micro_ros_agent_locator * locator = (struct micro_ros_agent_locator *) transport->args;
    const uint16_t local_port = 2018;

    if (udp_socket >= 0) {
      ::close(udp_socket);
      udp_socket = -1;
    }

    udp_socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (udp_socket < 0) {
      Serial.printf("UDP socket failed: errno=%d\n", errno);
      return false;
    }

    int reuse = 1;
    setsockopt(udp_socket, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

    // Entity creation responses arrive as short back-to-back datagrams.
    // Keep enough socket queue space so both status and heartbeat are retained.
    int receive_buffer_size = 16 * 1024;
    setsockopt(udp_socket, SOL_SOCKET, SO_RCVBUF,
               &receive_buffer_size, sizeof(receive_buffer_size));

    struct sockaddr_in local_address = {};
    local_address.sin_family = AF_INET;
    local_address.sin_port = htons(local_port);
    local_address.sin_addr.s_addr = INADDR_ANY;
    if (bind(udp_socket, (struct sockaddr *) &local_address,
             sizeof(local_address)) < 0) {
      Serial.printf("UDP bind failed: errno=%d\n", errno);
      ::close(udp_socket);
      udp_socket = -1;
      return false;
    }

    agent_address = {};
    agent_address.sin_family = AF_INET;
    agent_address.sin_port = htons(locator->port);
    agent_address.sin_addr.s_addr = (uint32_t) locator->address;
    if (connect(udp_socket, (struct sockaddr *) &agent_address,
                sizeof(agent_address)) < 0) {
      Serial.printf("UDP connect failed: errno=%d\n", errno);
      ::close(udp_socket);
      udp_socket = -1;
      return false;
    }

    Serial.printf("UDP open: local=%u remote=%d raw-socket\n",
                  local_port, locator->port);
    return true;
  }

  bool arduino_wifi_transport_close(struct uxrCustomTransport * transport)
  {
    (void) transport;
    if (udp_socket >= 0) {
      ::close(udp_socket);
      udp_socket = -1;
    }
    return true;
  }

  size_t arduino_wifi_transport_write(struct uxrCustomTransport * transport, const uint8_t *buf, size_t len, uint8_t *errcode)
  {
    (void) transport;
    ssize_t sent = udp_socket >= 0 ? send(udp_socket, buf, len, 0) : -1;
    record_udp_trace('W', (int) len, 0, (int) sent,
                     sent < 0 ? errno : 0);

    if (errcode != NULL) {
      *errcode = (sent == (ssize_t) len) ? 0 : 1;
    }

    return sent < 0 ? 0 : (size_t) sent;
  }

  size_t arduino_wifi_transport_read(struct uxrCustomTransport * transport, uint8_t *buf, size_t len, int timeout, uint8_t *errcode)
  {
    (void) transport;

    if (udp_socket < 0) {
      record_udp_trace('R', (int) len, timeout, 0, -1);
      if (errcode != NULL) {
        *errcode = 1;
      }
      return 0;
    }

    fd_set read_set;
    FD_ZERO(&read_set);
    FD_SET(udp_socket, &read_set);

    struct timeval wait_time = {};
    wait_time.tv_sec = timeout > 0 ? timeout / 1000 : 0;
    wait_time.tv_usec = timeout > 0 ? (timeout % 1000) * 1000 : 0;

    int ready = select(udp_socket + 1, &read_set, NULL, NULL, &wait_time);
    if (ready <= 0) {
      record_udp_trace('R', (int) len, timeout, 0,
                       ready < 0 ? errno : 0);
      if (errcode != NULL) {
        *errcode = ready < 0 ? 1 : 0;
      }
      return 0;
    }

    ssize_t received = recv(udp_socket, buf, len, 0);
    record_udp_trace('R', (int) len, timeout, (int) received,
                     received < 0 ? errno : ready);
    if (errcode != NULL) {
      *errcode = received < 0 ? 1 : 0;
    }

    return received < 0 ? 0 : (size_t) received;
  }
}

#endif
