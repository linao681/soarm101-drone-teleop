#include <unity.h>

#include "agent_discovery_protocol.h"

void test_valid_announcement() {
    agent_discovery::Announcement result{};
    const char payload[] = "SOARM_AGENT 1 1234abcd 8888\n";

    TEST_ASSERT_TRUE(agent_discovery::parse_announcement(
        payload, sizeof(payload) - 1, result));
    TEST_ASSERT_EQUAL_HEX32(0x1234abcd, result.nonce);
    TEST_ASSERT_EQUAL_UINT16(8888, result.agent_port);
}

void test_invalid_announcements() {
    agent_discovery::Announcement result{};
    const char wrong_version[] = "SOARM_AGENT 2 1234abcd 8888\n";
    const char bad_nonce[] = "SOARM_AGENT 1 zzzzabcd 8888\n";
    const char bad_port[] = "SOARM_AGENT 1 1234abcd 0\n";

    TEST_ASSERT_FALSE(agent_discovery::parse_announcement(
        wrong_version, sizeof(wrong_version) - 1, result));
    TEST_ASSERT_FALSE(agent_discovery::parse_announcement(
        bad_nonce, sizeof(bad_nonce) - 1, result));
    TEST_ASSERT_FALSE(agent_discovery::parse_announcement(
        bad_port, sizeof(bad_port) - 1, result));
}

void test_announcement_rejects_trailing_bytes_and_extra_fields() {
    agent_discovery::Announcement result{};
    const char trailing[] = "SOARM_AGENT 1 1234abcd 8888\nextra";
    const char extra_field[] = "SOARM_AGENT 1 1234abcd 8888 extra\n";

    TEST_ASSERT_FALSE(agent_discovery::parse_announcement(
        trailing, sizeof(trailing) - 1, result));
    TEST_ASSERT_FALSE(agent_discovery::parse_announcement(
        extra_field, sizeof(extra_field) - 1, result));
}

void test_announcement_rejects_invalid_port_range() {
    agent_discovery::Announcement result{};
    const char too_large[] = "SOARM_AGENT 1 1234abcd 65536\n";

    TEST_ASSERT_FALSE(agent_discovery::parse_announcement(
        too_large, sizeof(too_large) - 1, result));
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_valid_announcement);
    RUN_TEST(test_invalid_announcements);
    RUN_TEST(test_announcement_rejects_trailing_bytes_and_extra_fields);
    RUN_TEST(test_announcement_rejects_invalid_port_range);
    return UNITY_END();
}
