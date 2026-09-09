#ifndef SOARM_COMMON_AGENT_DISCOVERY_PROTOCOL_H_
#define SOARM_COMMON_AGENT_DISCOVERY_PROTOCOL_H_

#include <cstddef>
#include <cstdint>

namespace agent_discovery {

constexpr uint16_t kDiscoveryPort = 8889;
constexpr char kProbe[] = "SOARM_DISCOVER 1\n";

struct Announcement {
    uint32_t nonce;
    uint16_t agent_port;
};

inline bool parse_announcement(const char* data, size_t size, Announcement& output) {
    constexpr char kPrefix[] = "SOARM_AGENT ";
    constexpr size_t kNonceLength = 8;
    constexpr size_t kMaxPortLength = 5;

    if (data == nullptr || size <= sizeof(kPrefix) - 1) {
        return false;
    }

    size_t position = 0;
    for (size_t index = 0; index < sizeof(kPrefix) - 1; ++index) {
        if (data[position++] != kPrefix[index]) {
            return false;
        }
    }

    if (position + 2 > size || data[position++] != '1' || data[position++] != ' ') {
        return false;
    }

    char nonce_text[kNonceLength + 1]{};
    for (size_t index = 0; index < kNonceLength; ++index) {
        if (position >= size || data[position] == ' ' || data[position] == '\n') {
            return false;
        }
        nonce_text[index] = data[position++];
    }
    if (position >= size || data[position++] != ' ') {
        return false;
    }

    uint32_t nonce = 0;
    for (size_t index = 0; index < kNonceLength; ++index) {
        const char digit = nonce_text[index];
        uint8_t value = 0;
        if (digit >= '0' && digit <= '9') {
            value = static_cast<uint8_t>(digit - '0');
        } else if (digit >= 'a' && digit <= 'f') {
            value = static_cast<uint8_t>(digit - 'a' + 10);
        } else if (digit >= 'A' && digit <= 'F') {
            value = static_cast<uint8_t>(digit - 'A' + 10);
        } else {
            return false;
        }
        nonce = (nonce << 4) | value;
    }

    char port_text[kMaxPortLength + 1]{};
    size_t port_length = 0;
    while (position < size && data[position] != '\n') {
        if (port_length == kMaxPortLength) {
            return false;
        }
        port_text[port_length++] = data[position++];
    }
    if (port_length == 0 || position >= size || data[position++] != '\n' || position != size) {
        return false;
    }

    uint32_t port = 0;
    for (size_t index = 0; index < port_length; ++index) {
        const char digit = port_text[index];
        if (digit < '0' || digit > '9') {
            return false;
        }
        port = port * 10 + static_cast<uint32_t>(digit - '0');
        if (port > 65535) {
            return false;
        }
    }
    if (port == 0) {
        return false;
    }

    output.nonce = nonce;
    output.agent_port = static_cast<uint16_t>(port);
    return true;
}

}  // namespace agent_discovery

#endif
