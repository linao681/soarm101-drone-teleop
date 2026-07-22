// generated from rosidl_generator_c/resource/idl__description.c.em
// with input from rosgraph_msgs:msg/QoSProfile.idl
// generated code does not contain a copyright notice

#include "rosgraph_msgs/msg/detail/qo_s_profile__functions.h"

ROSIDL_GENERATOR_C_PUBLIC_rosgraph_msgs
const rosidl_type_hash_t *
rosgraph_msgs__msg__QoSProfile__get_type_hash(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_type_hash_t hash = {1, {
      0x0c, 0x83, 0x30, 0x5c, 0x2c, 0x64, 0x7e, 0xec,
      0xbf, 0x3a, 0x0a, 0xd5, 0x49, 0xc1, 0x21, 0xd6,
      0xcf, 0x12, 0x60, 0x6d, 0x90, 0x29, 0x15, 0xa2,
      0x8e, 0x90, 0x4d, 0x8f, 0x2a, 0xba, 0x42, 0xee,
    }};
  return &hash;
}

#include <assert.h>
#include <string.h>

// Include directives for referenced types
#include "builtin_interfaces/msg/detail/duration__functions.h"

// Hashes for external referenced types
#ifndef NDEBUG
static const rosidl_type_hash_t builtin_interfaces__msg__Duration__EXPECTED_HASH = {1, {
    0xe8, 0xd0, 0x09, 0xf6, 0x59, 0x81, 0x6f, 0x75,
    0x8b, 0x75, 0x33, 0x4e, 0xe1, 0xa9, 0xca, 0x5b,
    0x5c, 0x0b, 0x85, 0x98, 0x43, 0x26, 0x1f, 0x14,
    0xc7, 0xf9, 0x37, 0x34, 0x95, 0x99, 0xd9, 0x3b,
  }};
#endif

static char rosgraph_msgs__msg__QoSProfile__TYPE_NAME[] = "rosgraph_msgs/msg/QoSProfile";
static char builtin_interfaces__msg__Duration__TYPE_NAME[] = "builtin_interfaces/msg/Duration";

// Define type names, field names, and default values
static char rosgraph_msgs__msg__QoSProfile__FIELD_NAME__depth[] = "depth";
static char rosgraph_msgs__msg__QoSProfile__FIELD_NAME__deadline[] = "deadline";
static char rosgraph_msgs__msg__QoSProfile__FIELD_NAME__lifespan[] = "lifespan";
static char rosgraph_msgs__msg__QoSProfile__FIELD_NAME__history[] = "history";
static char rosgraph_msgs__msg__QoSProfile__FIELD_NAME__reliability[] = "reliability";
static char rosgraph_msgs__msg__QoSProfile__FIELD_NAME__durability[] = "durability";
static char rosgraph_msgs__msg__QoSProfile__FIELD_NAME__liveliness[] = "liveliness";
static char rosgraph_msgs__msg__QoSProfile__FIELD_NAME__liveliness_lease_duration[] = "liveliness_lease_duration";

static rosidl_runtime_c__type_description__Field rosgraph_msgs__msg__QoSProfile__FIELDS[] = {
  {
    {rosgraph_msgs__msg__QoSProfile__FIELD_NAME__depth, 5, 5},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_UINT32,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__QoSProfile__FIELD_NAME__deadline, 8, 8},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {builtin_interfaces__msg__Duration__TYPE_NAME, 31, 31},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__QoSProfile__FIELD_NAME__lifespan, 8, 8},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {builtin_interfaces__msg__Duration__TYPE_NAME, 31, 31},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__QoSProfile__FIELD_NAME__history, 7, 7},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_UINT8,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__QoSProfile__FIELD_NAME__reliability, 11, 11},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_UINT8,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__QoSProfile__FIELD_NAME__durability, 10, 10},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_UINT8,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__QoSProfile__FIELD_NAME__liveliness, 10, 10},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_UINT8,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__QoSProfile__FIELD_NAME__liveliness_lease_duration, 25, 25},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {builtin_interfaces__msg__Duration__TYPE_NAME, 31, 31},
    },
    {NULL, 0, 0},
  },
};

static rosidl_runtime_c__type_description__IndividualTypeDescription rosgraph_msgs__msg__QoSProfile__REFERENCED_TYPE_DESCRIPTIONS[] = {
  {
    {builtin_interfaces__msg__Duration__TYPE_NAME, 31, 31},
    {NULL, 0, 0},
  },
};

const rosidl_runtime_c__type_description__TypeDescription *
rosgraph_msgs__msg__QoSProfile__get_type_description(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static bool constructed = false;
  static const rosidl_runtime_c__type_description__TypeDescription description = {
    {
      {rosgraph_msgs__msg__QoSProfile__TYPE_NAME, 28, 28},
      {rosgraph_msgs__msg__QoSProfile__FIELDS, 8, 8},
    },
    {rosgraph_msgs__msg__QoSProfile__REFERENCED_TYPE_DESCRIPTIONS, 1, 1},
  };
  if (!constructed) {
    assert(0 == memcmp(&builtin_interfaces__msg__Duration__EXPECTED_HASH, builtin_interfaces__msg__Duration__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[0].fields = builtin_interfaces__msg__Duration__get_type_description(NULL)->type_description.fields;
    constructed = true;
  }
  return &description;
}

static char toplevel_type_raw_source[] =
  "# Message-based representation of ROS 2 Quality of Service settings\n"
  "# Default values are kept in sync with RMW by integration test\n"
  "# Note that SYSTEM_DEFAULT and BEST_AVAILABLE values cannot be an observed value,\n"
  "# because they resolve concretely at runtime.\n"
  "# They are included here for completeness to match the data structures in RMW\n"
  "\n"
  "# Depth of the message queue (only meaningful when history==KEEP_LAST)\n"
  "uint32 depth\n"
  "\n"
  "# Deadline between messages (0 for no deadline)\n"
  "builtin_interfaces/Duration deadline\n"
  "\n"
  "# Lifespan of each message (0 for infinite)\n"
  "builtin_interfaces/Duration lifespan\n"
  "\n"
  "# History policy\n"
  "uint8 HISTORY_SYSTEM_DEFAULT=0\n"
  "uint8 HISTORY_KEEP_LAST=1\n"
  "uint8 HISTORY_KEEP_ALL=2\n"
  "uint8 HISTORY_UNKNOWN=3\n"
  "uint8 history\n"
  "\n"
  "# Reliability policy\n"
  "uint8 RELIABILITY_SYSTEM_DEFAULT=0\n"
  "uint8 RELIABILITY_RELIABLE=1\n"
  "uint8 RELIABILITY_BEST_EFFORT=2\n"
  "uint8 RELIABILITY_UNKNOWN=3\n"
  "uint8 RELIABILITY_BEST_AVAILABLE=4\n"
  "uint8 reliability\n"
  "\n"
  "# Durability policy\n"
  "uint8 DURABILITY_SYSTEM_DEFAULT=0\n"
  "uint8 DURABILITY_TRANSIENT_LOCAL=1\n"
  "uint8 DURABILITY_VOLATILE=2\n"
  "uint8 DURABILITY_UNKNOWN=3\n"
  "uint8 DURABILITY_BEST_AVAILABLE=4\n"
  "uint8 durability\n"
  "\n"
  "# Liveliness policy\n"
  "uint8 LIVELINESS_SYSTEM_DEFAULT=0\n"
  "uint8 LIVELINESS_AUTOMATIC=1\n"
  "uint8 LIVELINESS_MANUAL_BY_TOPIC=3\n"
  "uint8 LIVELINESS_UNKNOWN=4\n"
  "uint8 LIVELINESS_BEST_AVAILABLE=5\n"
  "uint8 liveliness\n"
  "\n"
  "# Lease duration for liveliness (0 for infinite)\n"
  "builtin_interfaces/Duration liveliness_lease_duration";

static char msg_encoding[] = "msg";

// Define all individual source functions

const rosidl_runtime_c__type_description__TypeSource *
rosgraph_msgs__msg__QoSProfile__get_individual_type_description_source(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static const rosidl_runtime_c__type_description__TypeSource source = {
    {rosgraph_msgs__msg__QoSProfile__TYPE_NAME, 28, 28},
    {msg_encoding, 3, 3},
    {toplevel_type_raw_source, 1424, 1424},
  };
  return &source;
}

const rosidl_runtime_c__type_description__TypeSource__Sequence *
rosgraph_msgs__msg__QoSProfile__get_type_description_sources(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_runtime_c__type_description__TypeSource sources[2];
  static const rosidl_runtime_c__type_description__TypeSource__Sequence source_sequence = {sources, 2, 2};
  static bool constructed = false;
  if (!constructed) {
    sources[0] = *rosgraph_msgs__msg__QoSProfile__get_individual_type_description_source(NULL),
    sources[1] = *builtin_interfaces__msg__Duration__get_individual_type_description_source(NULL);
    constructed = true;
  }
  return &source_sequence;
}
