#pragma once

// Reuse the generated shared configuration, then apply capacities that are
// specific to the leader firmware. The follower keeps including the shared
// header directly through its existing include path.
#include_next <rmw_microxrcedds_c/config.h>

#undef RMW_UXRCE_MAX_PUBLISHERS
#define RMW_UXRCE_MAX_PUBLISHERS 2

#undef RMW_UXRCE_MAX_SUBSCRIPTIONS
#define RMW_UXRCE_MAX_SUBSCRIPTIONS 0

#undef RMW_UXRCE_MAX_SERVICES
#define RMW_UXRCE_MAX_SERVICES 0

#undef RMW_UXRCE_MAX_CLIENTS
#define RMW_UXRCE_MAX_CLIENTS 0

#undef RMW_UXRCE_MAX_TOPICS
#define RMW_UXRCE_MAX_TOPICS 2

#undef RMW_UXRCE_MAX_TOPICS_INTERNAL
#define RMW_UXRCE_MAX_TOPICS_INTERNAL 2
