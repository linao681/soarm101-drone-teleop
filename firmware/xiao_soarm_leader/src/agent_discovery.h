#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#include "agent_discovery_protocol.h"

namespace leader_discovery {

class Discovery {
public:
    void begin();
    bool poll();
    bool has_agent() const;
    const IPAddress& agent_ip() const;
    uint16_t agent_port() const;

private:
    void send_probe_if_due(uint32_t now_ms);
    bool is_supported_subnet() const;

    WiFiUDP udp_;
    IPAddress agent_ip_;
    uint16_t agent_port_ = 0;
    uint32_t listen_started_ms_ = 0;
    uint32_t next_probe_ms_ = 0;
    uint8_t next_probe_host_ = 1;
    bool has_agent_ = false;
    bool unsupported_reported_ = false;
};

}  // namespace leader_discovery
