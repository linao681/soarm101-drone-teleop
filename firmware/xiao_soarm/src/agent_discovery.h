#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#include "../../soarm_common/agent_discovery_protocol.h"

namespace agent_discovery {

struct Agent {
    IPAddress ip;
    uint16_t port;
};

Agent discover();

}  // namespace agent_discovery
