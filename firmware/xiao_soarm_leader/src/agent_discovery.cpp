#include "agent_discovery.h"

#include <cstring>

namespace leader_discovery {
namespace {

constexpr uint32_t kProbeDelayMs = 3000;
constexpr uint32_t kProbeIntervalMs = 20;
constexpr uint8_t kFirstHost = 1;
constexpr uint8_t kLastHost = 254;
constexpr size_t kPacketCapacity = 64;

}  // namespace

void Discovery::begin() {
    udp_.begin(agent_discovery::kDiscoveryPort);
    listen_started_ms_ = millis();
    next_probe_ms_ = listen_started_ms_ + kProbeDelayMs;
    next_probe_host_ = kFirstHost;
    has_agent_ = false;
    unsupported_reported_ = false;
}

bool Discovery::poll() {
    const uint32_t now_ms = millis();
    const int packet_size = udp_.parsePacket();
    if (packet_size > 0) {
        char packet[kPacketCapacity] = {};
        const size_t length = static_cast<size_t>(packet_size);
        const size_t read_length = length < sizeof(packet) ? length : sizeof(packet);
        const int received = udp_.read(packet, read_length);
        agent_discovery::Announcement announcement{};
        if (received > 0 && agent_discovery::parse_announcement(
                packet, static_cast<size_t>(received), announcement)) {
            agent_ip_ = udp_.remoteIP();
            agent_port_ = announcement.agent_port;
            has_agent_ = true;
            return true;
        }
    }

    send_probe_if_due(now_ms);
    return false;
}

bool Discovery::has_agent() const {
    return has_agent_;
}

const IPAddress& Discovery::agent_ip() const {
    return agent_ip_;
}

uint16_t Discovery::agent_port() const {
    return agent_port_;
}

bool Discovery::is_supported_subnet() const {
    return WiFi.subnetMask() == IPAddress(255, 255, 255, 0);
}

void Discovery::send_probe_if_due(uint32_t now_ms) {
    if (has_agent_ || static_cast<uint32_t>(now_ms - listen_started_ms_) < kProbeDelayMs ||
        static_cast<int32_t>(now_ms - next_probe_ms_) < 0) {
        return;
    }

    if (!is_supported_subnet()) {
        if (!unsupported_reported_) {
            Serial.println("DISCOVERY_UNSUPPORTED_SUBNET");
            unsupported_reported_ = true;
        }
        return;
    }

    const IPAddress local = WiFi.localIP();
    const IPAddress target(local[0], local[1], local[2], next_probe_host_);
    udp_.beginPacket(target, agent_discovery::kDiscoveryPort);
    udp_.write(reinterpret_cast<const uint8_t*>(agent_discovery::kProbe),
        strlen(agent_discovery::kProbe));
    udp_.endPacket();

    next_probe_host_++;
    if (next_probe_host_ > kLastHost) {
        next_probe_host_ = kFirstHost;
    }
    next_probe_ms_ = now_ms + kProbeIntervalMs;
}

}  // namespace leader_discovery
