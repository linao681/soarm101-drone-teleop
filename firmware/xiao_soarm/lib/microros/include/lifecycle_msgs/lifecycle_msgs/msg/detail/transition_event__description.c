// generated from rosidl_generator_c/resource/idl__description.c.em
// with input from lifecycle_msgs:msg/TransitionEvent.idl
// generated code does not contain a copyright notice

#include "lifecycle_msgs/msg/detail/transition_event__functions.h"

ROSIDL_GENERATOR_C_PUBLIC_lifecycle_msgs
const rosidl_type_hash_t *
lifecycle_msgs__msg__TransitionEvent__get_type_hash(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_type_hash_t hash = {1, {
      0x78, 0xb1, 0x9e, 0x2b, 0xe4, 0x1a, 0x79, 0x7f,
      0xc0, 0x09, 0xc9, 0x6b, 0xda, 0x68, 0x94, 0x41,
      0x82, 0xed, 0xab, 0xec, 0x78, 0x52, 0xcc, 0xcd,
      0x92, 0x8a, 0x40, 0xbc, 0x06, 0xf6, 0xf9, 0xd7,
    }};
  return &hash;
}

#include <assert.h>
#include <string.h>

// Include directives for referenced types
#include "builtin_interfaces/msg/detail/time__functions.h"
#include "lifecycle_msgs/msg/detail/state__functions.h"
#include "lifecycle_msgs/msg/detail/transition__functions.h"

// Hashes for external referenced types
#ifndef NDEBUG
static const rosidl_type_hash_t builtin_interfaces__msg__Time__EXPECTED_HASH = {1, {
    0xb1, 0x06, 0x23, 0x5e, 0x25, 0xa4, 0xc5, 0xed,
    0x35, 0x09, 0x8a, 0xa0, 0xa6, 0x1a, 0x3e, 0xe9,
    0xc9, 0xb1, 0x8d, 0x19, 0x7f, 0x39, 0x8b, 0x0e,
    0x42, 0x06, 0xce, 0xa9, 0xac, 0xf9, 0xc1, 0x97,
  }};
static const rosidl_type_hash_t lifecycle_msgs__msg__State__EXPECTED_HASH = {1, {
    0xdd, 0x2d, 0x02, 0xb8, 0x2f, 0x3e, 0xbc, 0x85,
    0x8e, 0x53, 0xc4, 0x31, 0xb1, 0xe6, 0xe9, 0x1f,
    0x3f, 0xfc, 0x71, 0x43, 0x6f, 0xc8, 0x1d, 0x07,
    0x15, 0x21, 0x4a, 0xc6, 0xee, 0x21, 0x07, 0xa0,
  }};
static const rosidl_type_hash_t lifecycle_msgs__msg__Transition__EXPECTED_HASH = {1, {
    0xc6, 0x5d, 0x7b, 0x31, 0xea, 0x13, 0x4c, 0xba,
    0x4f, 0x54, 0xfc, 0x86, 0x7b, 0x81, 0x79, 0x79,
    0xbe, 0x79, 0x9f, 0x74, 0x52, 0x03, 0x5c, 0xd3,
    0x5f, 0xac, 0x9b, 0x74, 0x21, 0xfb, 0x34, 0x24,
  }};
#endif

static char lifecycle_msgs__msg__TransitionEvent__TYPE_NAME[] = "lifecycle_msgs/msg/TransitionEvent";
static char builtin_interfaces__msg__Time__TYPE_NAME[] = "builtin_interfaces/msg/Time";
static char lifecycle_msgs__msg__State__TYPE_NAME[] = "lifecycle_msgs/msg/State";
static char lifecycle_msgs__msg__Transition__TYPE_NAME[] = "lifecycle_msgs/msg/Transition";

// Define type names, field names, and default values
static char lifecycle_msgs__msg__TransitionEvent__FIELD_NAME__stamp[] = "stamp";
static char lifecycle_msgs__msg__TransitionEvent__FIELD_NAME__transition[] = "transition";
static char lifecycle_msgs__msg__TransitionEvent__FIELD_NAME__start_state[] = "start_state";
static char lifecycle_msgs__msg__TransitionEvent__FIELD_NAME__goal_state[] = "goal_state";

static rosidl_runtime_c__type_description__Field lifecycle_msgs__msg__TransitionEvent__FIELDS[] = {
  {
    {lifecycle_msgs__msg__TransitionEvent__FIELD_NAME__stamp, 5, 5},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {builtin_interfaces__msg__Time__TYPE_NAME, 27, 27},
    },
    {NULL, 0, 0},
  },
  {
    {lifecycle_msgs__msg__TransitionEvent__FIELD_NAME__transition, 10, 10},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {lifecycle_msgs__msg__Transition__TYPE_NAME, 29, 29},
    },
    {NULL, 0, 0},
  },
  {
    {lifecycle_msgs__msg__TransitionEvent__FIELD_NAME__start_state, 11, 11},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {lifecycle_msgs__msg__State__TYPE_NAME, 24, 24},
    },
    {NULL, 0, 0},
  },
  {
    {lifecycle_msgs__msg__TransitionEvent__FIELD_NAME__goal_state, 10, 10},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {lifecycle_msgs__msg__State__TYPE_NAME, 24, 24},
    },
    {NULL, 0, 0},
  },
};

static rosidl_runtime_c__type_description__IndividualTypeDescription lifecycle_msgs__msg__TransitionEvent__REFERENCED_TYPE_DESCRIPTIONS[] = {
  {
    {builtin_interfaces__msg__Time__TYPE_NAME, 27, 27},
    {NULL, 0, 0},
  },
  {
    {lifecycle_msgs__msg__State__TYPE_NAME, 24, 24},
    {NULL, 0, 0},
  },
  {
    {lifecycle_msgs__msg__Transition__TYPE_NAME, 29, 29},
    {NULL, 0, 0},
  },
};

const rosidl_runtime_c__type_description__TypeDescription *
lifecycle_msgs__msg__TransitionEvent__get_type_description(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static bool constructed = false;
  static const rosidl_runtime_c__type_description__TypeDescription description = {
    {
      {lifecycle_msgs__msg__TransitionEvent__TYPE_NAME, 34, 34},
      {lifecycle_msgs__msg__TransitionEvent__FIELDS, 4, 4},
    },
    {lifecycle_msgs__msg__TransitionEvent__REFERENCED_TYPE_DESCRIPTIONS, 3, 3},
  };
  if (!constructed) {
    assert(0 == memcmp(&builtin_interfaces__msg__Time__EXPECTED_HASH, builtin_interfaces__msg__Time__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[0].fields = builtin_interfaces__msg__Time__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&lifecycle_msgs__msg__State__EXPECTED_HASH, lifecycle_msgs__msg__State__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[1].fields = lifecycle_msgs__msg__State__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&lifecycle_msgs__msg__Transition__EXPECTED_HASH, lifecycle_msgs__msg__Transition__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[2].fields = lifecycle_msgs__msg__Transition__get_type_description(NULL)->type_description.fields;
    constructed = true;
  }
  return &description;
}

static char toplevel_type_raw_source[] =
  "# The time point at which this event occurred.\n"
  "builtin_interfaces/Time stamp\n"
  "\n"
  "# The id and label of this transition event.\n"
  "Transition transition\n"
  "\n"
  "# The starting state from which this event transitioned.\n"
  "State start_state\n"
  "\n"
  "# The end state of this transition event.\n"
  "State goal_state";

static char msg_encoding[] = "msg";

// Define all individual source functions

const rosidl_runtime_c__type_description__TypeSource *
lifecycle_msgs__msg__TransitionEvent__get_individual_type_description_source(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static const rosidl_runtime_c__type_description__TypeSource source = {
    {lifecycle_msgs__msg__TransitionEvent__TYPE_NAME, 34, 34},
    {msg_encoding, 3, 3},
    {toplevel_type_raw_source, 281, 281},
  };
  return &source;
}

const rosidl_runtime_c__type_description__TypeSource__Sequence *
lifecycle_msgs__msg__TransitionEvent__get_type_description_sources(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_runtime_c__type_description__TypeSource sources[4];
  static const rosidl_runtime_c__type_description__TypeSource__Sequence source_sequence = {sources, 4, 4};
  static bool constructed = false;
  if (!constructed) {
    sources[0] = *lifecycle_msgs__msg__TransitionEvent__get_individual_type_description_source(NULL),
    sources[1] = *builtin_interfaces__msg__Time__get_individual_type_description_source(NULL);
    sources[2] = *lifecycle_msgs__msg__State__get_individual_type_description_source(NULL);
    sources[3] = *lifecycle_msgs__msg__Transition__get_individual_type_description_source(NULL);
    constructed = true;
  }
  return &source_sequence;
}
