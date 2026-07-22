// generated from rosidl_generator_c/resource/idl__description.c.em
// with input from rosgraph_msgs:msg/Node.idl
// generated code does not contain a copyright notice

#include "rosgraph_msgs/msg/detail/node__functions.h"

ROSIDL_GENERATOR_C_PUBLIC_rosgraph_msgs
const rosidl_type_hash_t *
rosgraph_msgs__msg__Node__get_type_hash(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_type_hash_t hash = {1, {
      0x22, 0x60, 0xc5, 0x12, 0x80, 0x39, 0x78, 0x35,
      0x15, 0xbd, 0x98, 0xbc, 0x77, 0xbb, 0xb4, 0x9a,
      0xe4, 0x75, 0x88, 0x18, 0xd9, 0xe3, 0xc6, 0x53,
      0x6b, 0x31, 0x3c, 0x20, 0x24, 0xc7, 0x70, 0x45,
    }};
  return &hash;
}

#include <assert.h>
#include <string.h>

// Include directives for referenced types
#include "builtin_interfaces/msg/detail/duration__functions.h"
#include "rcl_interfaces/msg/detail/floating_point_range__functions.h"
#include "rcl_interfaces/msg/detail/integer_range__functions.h"
#include "rcl_interfaces/msg/detail/parameter_descriptor__functions.h"
#include "rcl_interfaces/msg/detail/parameter_value__functions.h"
#include "rosgraph_msgs/msg/detail/action__functions.h"
#include "rosgraph_msgs/msg/detail/interface_type__functions.h"
#include "rosgraph_msgs/msg/detail/qo_s_profile__functions.h"
#include "rosgraph_msgs/msg/detail/service__functions.h"
#include "rosgraph_msgs/msg/detail/topic__functions.h"
#include "rosgraph_msgs/msg/detail/type_hash__functions.h"

// Hashes for external referenced types
#ifndef NDEBUG
static const rosidl_type_hash_t builtin_interfaces__msg__Duration__EXPECTED_HASH = {1, {
    0xe8, 0xd0, 0x09, 0xf6, 0x59, 0x81, 0x6f, 0x75,
    0x8b, 0x75, 0x33, 0x4e, 0xe1, 0xa9, 0xca, 0x5b,
    0x5c, 0x0b, 0x85, 0x98, 0x43, 0x26, 0x1f, 0x14,
    0xc7, 0xf9, 0x37, 0x34, 0x95, 0x99, 0xd9, 0x3b,
  }};
static const rosidl_type_hash_t rcl_interfaces__msg__FloatingPointRange__EXPECTED_HASH = {1, {
    0xe6, 0xaf, 0x23, 0xa2, 0x3c, 0x17, 0x7f, 0xee,
    0x5f, 0x30, 0x75, 0xc8, 0xb1, 0xe4, 0x35, 0x16,
    0x2a, 0x9b, 0x63, 0xc8, 0x63, 0xd7, 0x8c, 0x06,
    0x01, 0x74, 0x60, 0xb4, 0x96, 0x84, 0x26, 0x2d,
  }};
static const rosidl_type_hash_t rcl_interfaces__msg__IntegerRange__EXPECTED_HASH = {1, {
    0xf7, 0xb7, 0xfd, 0xc0, 0xf6, 0x5f, 0x07, 0x70,
    0x2e, 0x09, 0x92, 0x18, 0xe1, 0x32, 0x88, 0xc3,
    0x96, 0x3b, 0xcb, 0x93, 0x45, 0xbd, 0xe7, 0x8b,
    0x56, 0x0e, 0x6c, 0xd1, 0x98, 0x00, 0xfc, 0x5a,
  }};
static const rosidl_type_hash_t rcl_interfaces__msg__ParameterDescriptor__EXPECTED_HASH = {1, {
    0x52, 0x17, 0x5d, 0xbf, 0xda, 0x6c, 0x51, 0x15,
    0x31, 0x01, 0xd3, 0x3d, 0x2a, 0x9d, 0xa0, 0x57,
    0x43, 0xf6, 0x6f, 0x02, 0xd5, 0xab, 0x2c, 0xa9,
    0xec, 0x47, 0x09, 0xb4, 0x6b, 0x73, 0xd7, 0x04,
  }};
static const rosidl_type_hash_t rcl_interfaces__msg__ParameterValue__EXPECTED_HASH = {1, {
    0x11, 0x5f, 0xc0, 0x89, 0xa3, 0x87, 0xe2, 0x3c,
    0x7e, 0xcd, 0x35, 0x25, 0xc9, 0x18, 0x9c, 0x37,
    0x91, 0x09, 0x11, 0x9d, 0x6a, 0xb8, 0x2e, 0x8d,
    0xfb, 0xde, 0x0f, 0xdf, 0x6a, 0x7f, 0x9b, 0x68,
  }};
static const rosidl_type_hash_t rosgraph_msgs__msg__Action__EXPECTED_HASH = {1, {
    0x22, 0x1c, 0x3b, 0x8d, 0x63, 0x47, 0x0a, 0xdd,
    0x1e, 0xa7, 0x02, 0x31, 0xa2, 0xc5, 0xc3, 0x48,
    0x8b, 0xd0, 0xa1, 0x1f, 0xab, 0x7f, 0x4b, 0x87,
    0xbb, 0xf0, 0x6a, 0xd3, 0x41, 0x06, 0x2e, 0x39,
  }};
static const rosidl_type_hash_t rosgraph_msgs__msg__InterfaceType__EXPECTED_HASH = {1, {
    0x08, 0xe2, 0x22, 0xa0, 0xb6, 0x95, 0x0d, 0x27,
    0x5c, 0x45, 0xc2, 0x92, 0x4b, 0x6b, 0xb6, 0xb7,
    0x9b, 0x7f, 0xde, 0xde, 0x9c, 0x90, 0xcd, 0xf5,
    0xd6, 0x95, 0x2d, 0xc6, 0xf1, 0x97, 0x91, 0x6c,
  }};
static const rosidl_type_hash_t rosgraph_msgs__msg__QoSProfile__EXPECTED_HASH = {1, {
    0x0c, 0x83, 0x30, 0x5c, 0x2c, 0x64, 0x7e, 0xec,
    0xbf, 0x3a, 0x0a, 0xd5, 0x49, 0xc1, 0x21, 0xd6,
    0xcf, 0x12, 0x60, 0x6d, 0x90, 0x29, 0x15, 0xa2,
    0x8e, 0x90, 0x4d, 0x8f, 0x2a, 0xba, 0x42, 0xee,
  }};
static const rosidl_type_hash_t rosgraph_msgs__msg__Service__EXPECTED_HASH = {1, {
    0x01, 0xa8, 0x0e, 0x1d, 0xc0, 0x66, 0xd6, 0xf3,
    0x78, 0x46, 0xe0, 0x00, 0x29, 0x71, 0x0c, 0x39,
    0xcf, 0xdf, 0xd8, 0xc8, 0x07, 0xbe, 0x16, 0xf8,
    0xf6, 0x18, 0x1f, 0x58, 0x34, 0xf5, 0xc6, 0x79,
  }};
static const rosidl_type_hash_t rosgraph_msgs__msg__Topic__EXPECTED_HASH = {1, {
    0xe3, 0x78, 0xdf, 0xc4, 0x44, 0xe3, 0xe0, 0x4c,
    0x76, 0xff, 0xdd, 0xa3, 0xca, 0xa9, 0x97, 0xf1,
    0x07, 0xb6, 0xf2, 0xd9, 0xba, 0x05, 0x9f, 0xcf,
    0x09, 0xb2, 0xf3, 0x94, 0x33, 0xa1, 0x49, 0xe4,
  }};
static const rosidl_type_hash_t rosgraph_msgs__msg__TypeHash__EXPECTED_HASH = {1, {
    0xb5, 0x72, 0x48, 0xb9, 0xd4, 0xea, 0x09, 0x64,
    0xbd, 0x58, 0x3c, 0x53, 0xae, 0x3b, 0x94, 0x35,
    0x4e, 0x59, 0x9b, 0x81, 0x83, 0xa1, 0x35, 0xaf,
    0x48, 0x82, 0x62, 0x87, 0xbe, 0xf3, 0xc1, 0xf6,
  }};
#endif

static char rosgraph_msgs__msg__Node__TYPE_NAME[] = "rosgraph_msgs/msg/Node";
static char builtin_interfaces__msg__Duration__TYPE_NAME[] = "builtin_interfaces/msg/Duration";
static char rcl_interfaces__msg__FloatingPointRange__TYPE_NAME[] = "rcl_interfaces/msg/FloatingPointRange";
static char rcl_interfaces__msg__IntegerRange__TYPE_NAME[] = "rcl_interfaces/msg/IntegerRange";
static char rcl_interfaces__msg__ParameterDescriptor__TYPE_NAME[] = "rcl_interfaces/msg/ParameterDescriptor";
static char rcl_interfaces__msg__ParameterValue__TYPE_NAME[] = "rcl_interfaces/msg/ParameterValue";
static char rosgraph_msgs__msg__Action__TYPE_NAME[] = "rosgraph_msgs/msg/Action";
static char rosgraph_msgs__msg__InterfaceType__TYPE_NAME[] = "rosgraph_msgs/msg/InterfaceType";
static char rosgraph_msgs__msg__QoSProfile__TYPE_NAME[] = "rosgraph_msgs/msg/QoSProfile";
static char rosgraph_msgs__msg__Service__TYPE_NAME[] = "rosgraph_msgs/msg/Service";
static char rosgraph_msgs__msg__Topic__TYPE_NAME[] = "rosgraph_msgs/msg/Topic";
static char rosgraph_msgs__msg__TypeHash__TYPE_NAME[] = "rosgraph_msgs/msg/TypeHash";

// Define type names, field names, and default values
static char rosgraph_msgs__msg__Node__FIELD_NAME__name[] = "name";
static char rosgraph_msgs__msg__Node__FIELD_NAME__parameters[] = "parameters";
static char rosgraph_msgs__msg__Node__FIELD_NAME__parameter_values[] = "parameter_values";
static char rosgraph_msgs__msg__Node__FIELD_NAME__publishers[] = "publishers";
static char rosgraph_msgs__msg__Node__FIELD_NAME__subscriptions[] = "subscriptions";
static char rosgraph_msgs__msg__Node__FIELD_NAME__service_clients[] = "service_clients";
static char rosgraph_msgs__msg__Node__FIELD_NAME__service_servers[] = "service_servers";
static char rosgraph_msgs__msg__Node__FIELD_NAME__action_clients[] = "action_clients";
static char rosgraph_msgs__msg__Node__FIELD_NAME__action_servers[] = "action_servers";

static rosidl_runtime_c__type_description__Field rosgraph_msgs__msg__Node__FIELDS[] = {
  {
    {rosgraph_msgs__msg__Node__FIELD_NAME__name, 4, 4},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_STRING,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Node__FIELD_NAME__parameters, 10, 10},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE_UNBOUNDED_SEQUENCE,
      0,
      0,
      {rcl_interfaces__msg__ParameterDescriptor__TYPE_NAME, 38, 38},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Node__FIELD_NAME__parameter_values, 16, 16},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE_UNBOUNDED_SEQUENCE,
      0,
      0,
      {rcl_interfaces__msg__ParameterValue__TYPE_NAME, 33, 33},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Node__FIELD_NAME__publishers, 10, 10},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE_UNBOUNDED_SEQUENCE,
      0,
      0,
      {rosgraph_msgs__msg__Topic__TYPE_NAME, 23, 23},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Node__FIELD_NAME__subscriptions, 13, 13},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE_UNBOUNDED_SEQUENCE,
      0,
      0,
      {rosgraph_msgs__msg__Topic__TYPE_NAME, 23, 23},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Node__FIELD_NAME__service_clients, 15, 15},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE_UNBOUNDED_SEQUENCE,
      0,
      0,
      {rosgraph_msgs__msg__Service__TYPE_NAME, 25, 25},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Node__FIELD_NAME__service_servers, 15, 15},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE_UNBOUNDED_SEQUENCE,
      0,
      0,
      {rosgraph_msgs__msg__Service__TYPE_NAME, 25, 25},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Node__FIELD_NAME__action_clients, 14, 14},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE_UNBOUNDED_SEQUENCE,
      0,
      0,
      {rosgraph_msgs__msg__Action__TYPE_NAME, 24, 24},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Node__FIELD_NAME__action_servers, 14, 14},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE_UNBOUNDED_SEQUENCE,
      0,
      0,
      {rosgraph_msgs__msg__Action__TYPE_NAME, 24, 24},
    },
    {NULL, 0, 0},
  },
};

static rosidl_runtime_c__type_description__IndividualTypeDescription rosgraph_msgs__msg__Node__REFERENCED_TYPE_DESCRIPTIONS[] = {
  {
    {builtin_interfaces__msg__Duration__TYPE_NAME, 31, 31},
    {NULL, 0, 0},
  },
  {
    {rcl_interfaces__msg__FloatingPointRange__TYPE_NAME, 37, 37},
    {NULL, 0, 0},
  },
  {
    {rcl_interfaces__msg__IntegerRange__TYPE_NAME, 31, 31},
    {NULL, 0, 0},
  },
  {
    {rcl_interfaces__msg__ParameterDescriptor__TYPE_NAME, 38, 38},
    {NULL, 0, 0},
  },
  {
    {rcl_interfaces__msg__ParameterValue__TYPE_NAME, 33, 33},
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Action__TYPE_NAME, 24, 24},
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__InterfaceType__TYPE_NAME, 31, 31},
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__QoSProfile__TYPE_NAME, 28, 28},
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Service__TYPE_NAME, 25, 25},
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Topic__TYPE_NAME, 23, 23},
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__TypeHash__TYPE_NAME, 26, 26},
    {NULL, 0, 0},
  },
};

const rosidl_runtime_c__type_description__TypeDescription *
rosgraph_msgs__msg__Node__get_type_description(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static bool constructed = false;
  static const rosidl_runtime_c__type_description__TypeDescription description = {
    {
      {rosgraph_msgs__msg__Node__TYPE_NAME, 22, 22},
      {rosgraph_msgs__msg__Node__FIELDS, 9, 9},
    },
    {rosgraph_msgs__msg__Node__REFERENCED_TYPE_DESCRIPTIONS, 11, 11},
  };
  if (!constructed) {
    assert(0 == memcmp(&builtin_interfaces__msg__Duration__EXPECTED_HASH, builtin_interfaces__msg__Duration__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[0].fields = builtin_interfaces__msg__Duration__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rcl_interfaces__msg__FloatingPointRange__EXPECTED_HASH, rcl_interfaces__msg__FloatingPointRange__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[1].fields = rcl_interfaces__msg__FloatingPointRange__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rcl_interfaces__msg__IntegerRange__EXPECTED_HASH, rcl_interfaces__msg__IntegerRange__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[2].fields = rcl_interfaces__msg__IntegerRange__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rcl_interfaces__msg__ParameterDescriptor__EXPECTED_HASH, rcl_interfaces__msg__ParameterDescriptor__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[3].fields = rcl_interfaces__msg__ParameterDescriptor__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rcl_interfaces__msg__ParameterValue__EXPECTED_HASH, rcl_interfaces__msg__ParameterValue__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[4].fields = rcl_interfaces__msg__ParameterValue__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rosgraph_msgs__msg__Action__EXPECTED_HASH, rosgraph_msgs__msg__Action__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[5].fields = rosgraph_msgs__msg__Action__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rosgraph_msgs__msg__InterfaceType__EXPECTED_HASH, rosgraph_msgs__msg__InterfaceType__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[6].fields = rosgraph_msgs__msg__InterfaceType__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rosgraph_msgs__msg__QoSProfile__EXPECTED_HASH, rosgraph_msgs__msg__QoSProfile__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[7].fields = rosgraph_msgs__msg__QoSProfile__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rosgraph_msgs__msg__Service__EXPECTED_HASH, rosgraph_msgs__msg__Service__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[8].fields = rosgraph_msgs__msg__Service__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rosgraph_msgs__msg__Topic__EXPECTED_HASH, rosgraph_msgs__msg__Topic__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[9].fields = rosgraph_msgs__msg__Topic__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rosgraph_msgs__msg__TypeHash__EXPECTED_HASH, rosgraph_msgs__msg__TypeHash__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[10].fields = rosgraph_msgs__msg__TypeHash__get_type_description(NULL)->type_description.fields;
    constructed = true;
  }
  return &description;
}

static char toplevel_type_raw_source[] =
  "# Represents the observable runtime state of a ROS Node\n"
  "# Therefore, does not perfectly align with the abstract specification which created it.\n"
  "\n"
  "# Fully qualified node name (FQN)\n"
  "string name\n"
  "\n"
  "# Parameter specifications for the node\n"
  "rcl_interfaces/ParameterDescriptor[] parameters\n"
  "\n"
  "# Current values of the node's parameters\n"
  "# NOTE:\n"
  "#   parameter_values[] must be empty, or the same size as parameters[]\n"
  "#   When set, parameter_values[] match 1:1 with the same index in parameters[]\n"
  "rcl_interfaces/ParameterValue[] parameter_values\n"
  "\n"
  "# Communications endpoints - Topics, Services, and Actions\n"
  "Topic[] publishers\n"
  "Topic[] subscriptions\n"
  "\n"
  "Service[] service_clients\n"
  "Service[] service_servers\n"
  "\n"
  "Action[] action_clients\n"
  "Action[] action_servers";

static char msg_encoding[] = "msg";

// Define all individual source functions

const rosidl_runtime_c__type_description__TypeSource *
rosgraph_msgs__msg__Node__get_individual_type_description_source(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static const rosidl_runtime_c__type_description__TypeSource source = {
    {rosgraph_msgs__msg__Node__TYPE_NAME, 22, 22},
    {msg_encoding, 3, 3},
    {toplevel_type_raw_source, 733, 733},
  };
  return &source;
}

const rosidl_runtime_c__type_description__TypeSource__Sequence *
rosgraph_msgs__msg__Node__get_type_description_sources(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_runtime_c__type_description__TypeSource sources[12];
  static const rosidl_runtime_c__type_description__TypeSource__Sequence source_sequence = {sources, 12, 12};
  static bool constructed = false;
  if (!constructed) {
    sources[0] = *rosgraph_msgs__msg__Node__get_individual_type_description_source(NULL),
    sources[1] = *builtin_interfaces__msg__Duration__get_individual_type_description_source(NULL);
    sources[2] = *rcl_interfaces__msg__FloatingPointRange__get_individual_type_description_source(NULL);
    sources[3] = *rcl_interfaces__msg__IntegerRange__get_individual_type_description_source(NULL);
    sources[4] = *rcl_interfaces__msg__ParameterDescriptor__get_individual_type_description_source(NULL);
    sources[5] = *rcl_interfaces__msg__ParameterValue__get_individual_type_description_source(NULL);
    sources[6] = *rosgraph_msgs__msg__Action__get_individual_type_description_source(NULL);
    sources[7] = *rosgraph_msgs__msg__InterfaceType__get_individual_type_description_source(NULL);
    sources[8] = *rosgraph_msgs__msg__QoSProfile__get_individual_type_description_source(NULL);
    sources[9] = *rosgraph_msgs__msg__Service__get_individual_type_description_source(NULL);
    sources[10] = *rosgraph_msgs__msg__Topic__get_individual_type_description_source(NULL);
    sources[11] = *rosgraph_msgs__msg__TypeHash__get_individual_type_description_source(NULL);
    constructed = true;
  }
  return &source_sequence;
}
