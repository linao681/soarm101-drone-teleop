// generated from rosidl_generator_c/resource/idl__description.c.em
// with input from rosgraph_msgs:msg/Service.idl
// generated code does not contain a copyright notice

#include "rosgraph_msgs/msg/detail/service__functions.h"

ROSIDL_GENERATOR_C_PUBLIC_rosgraph_msgs
const rosidl_type_hash_t *
rosgraph_msgs__msg__Service__get_type_hash(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_type_hash_t hash = {1, {
      0x01, 0xa8, 0x0e, 0x1d, 0xc0, 0x66, 0xd6, 0xf3,
      0x78, 0x46, 0xe0, 0x00, 0x29, 0x71, 0x0c, 0x39,
      0xcf, 0xdf, 0xd8, 0xc8, 0x07, 0xbe, 0x16, 0xf8,
      0xf6, 0x18, 0x1f, 0x58, 0x34, 0xf5, 0xc6, 0x79,
    }};
  return &hash;
}

#include <assert.h>
#include <string.h>

// Include directives for referenced types
#include "builtin_interfaces/msg/detail/duration__functions.h"
#include "rosgraph_msgs/msg/detail/interface_type__functions.h"
#include "rosgraph_msgs/msg/detail/qo_s_profile__functions.h"
#include "rosgraph_msgs/msg/detail/type_hash__functions.h"

// Hashes for external referenced types
#ifndef NDEBUG
static const rosidl_type_hash_t builtin_interfaces__msg__Duration__EXPECTED_HASH = {1, {
    0xe8, 0xd0, 0x09, 0xf6, 0x59, 0x81, 0x6f, 0x75,
    0x8b, 0x75, 0x33, 0x4e, 0xe1, 0xa9, 0xca, 0x5b,
    0x5c, 0x0b, 0x85, 0x98, 0x43, 0x26, 0x1f, 0x14,
    0xc7, 0xf9, 0x37, 0x34, 0x95, 0x99, 0xd9, 0x3b,
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
static const rosidl_type_hash_t rosgraph_msgs__msg__TypeHash__EXPECTED_HASH = {1, {
    0xb5, 0x72, 0x48, 0xb9, 0xd4, 0xea, 0x09, 0x64,
    0xbd, 0x58, 0x3c, 0x53, 0xae, 0x3b, 0x94, 0x35,
    0x4e, 0x59, 0x9b, 0x81, 0x83, 0xa1, 0x35, 0xaf,
    0x48, 0x82, 0x62, 0x87, 0xbe, 0xf3, 0xc1, 0xf6,
  }};
#endif

static char rosgraph_msgs__msg__Service__TYPE_NAME[] = "rosgraph_msgs/msg/Service";
static char builtin_interfaces__msg__Duration__TYPE_NAME[] = "builtin_interfaces/msg/Duration";
static char rosgraph_msgs__msg__InterfaceType__TYPE_NAME[] = "rosgraph_msgs/msg/InterfaceType";
static char rosgraph_msgs__msg__QoSProfile__TYPE_NAME[] = "rosgraph_msgs/msg/QoSProfile";
static char rosgraph_msgs__msg__TypeHash__TYPE_NAME[] = "rosgraph_msgs/msg/TypeHash";

// Define type names, field names, and default values
static char rosgraph_msgs__msg__Service__FIELD_NAME__name[] = "name";
static char rosgraph_msgs__msg__Service__FIELD_NAME__request_type[] = "request_type";
static char rosgraph_msgs__msg__Service__FIELD_NAME__request_qos[] = "request_qos";
static char rosgraph_msgs__msg__Service__FIELD_NAME__response_type[] = "response_type";
static char rosgraph_msgs__msg__Service__FIELD_NAME__response_qos[] = "response_qos";

static rosidl_runtime_c__type_description__Field rosgraph_msgs__msg__Service__FIELDS[] = {
  {
    {rosgraph_msgs__msg__Service__FIELD_NAME__name, 4, 4},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_STRING,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Service__FIELD_NAME__request_type, 12, 12},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {rosgraph_msgs__msg__InterfaceType__TYPE_NAME, 31, 31},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Service__FIELD_NAME__request_qos, 11, 11},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {rosgraph_msgs__msg__QoSProfile__TYPE_NAME, 28, 28},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Service__FIELD_NAME__response_type, 13, 13},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {rosgraph_msgs__msg__InterfaceType__TYPE_NAME, 31, 31},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__Service__FIELD_NAME__response_qos, 12, 12},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {rosgraph_msgs__msg__QoSProfile__TYPE_NAME, 28, 28},
    },
    {NULL, 0, 0},
  },
};

static rosidl_runtime_c__type_description__IndividualTypeDescription rosgraph_msgs__msg__Service__REFERENCED_TYPE_DESCRIPTIONS[] = {
  {
    {builtin_interfaces__msg__Duration__TYPE_NAME, 31, 31},
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
    {rosgraph_msgs__msg__TypeHash__TYPE_NAME, 26, 26},
    {NULL, 0, 0},
  },
};

const rosidl_runtime_c__type_description__TypeDescription *
rosgraph_msgs__msg__Service__get_type_description(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static bool constructed = false;
  static const rosidl_runtime_c__type_description__TypeDescription description = {
    {
      {rosgraph_msgs__msg__Service__TYPE_NAME, 25, 25},
      {rosgraph_msgs__msg__Service__FIELDS, 5, 5},
    },
    {rosgraph_msgs__msg__Service__REFERENCED_TYPE_DESCRIPTIONS, 4, 4},
  };
  if (!constructed) {
    assert(0 == memcmp(&builtin_interfaces__msg__Duration__EXPECTED_HASH, builtin_interfaces__msg__Duration__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[0].fields = builtin_interfaces__msg__Duration__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rosgraph_msgs__msg__InterfaceType__EXPECTED_HASH, rosgraph_msgs__msg__InterfaceType__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[1].fields = rosgraph_msgs__msg__InterfaceType__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rosgraph_msgs__msg__QoSProfile__EXPECTED_HASH, rosgraph_msgs__msg__QoSProfile__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[2].fields = rosgraph_msgs__msg__QoSProfile__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&rosgraph_msgs__msg__TypeHash__EXPECTED_HASH, rosgraph_msgs__msg__TypeHash__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[3].fields = rosgraph_msgs__msg__TypeHash__get_type_description(NULL)->type_description.fields;
    constructed = true;
  }
  return &description;
}

static char toplevel_type_raw_source[] =
  "# Describes a single Service endpoint, which may be a Server or Client\n"
  "\n"
  "# Fully qualified name of the Service\n"
  "string name\n"
  "\n"
  "# Type and actual QoS of the request publisher (Client) or subscription (Server)\n"
  "InterfaceType request_type\n"
  "QoSProfile request_qos\n"
  "\n"
  "# Type and actual QoS of the request subscription (Client) or publisher (Server)\n"
  "InterfaceType response_type\n"
  "QoSProfile response_qos";

static char msg_encoding[] = "msg";

// Define all individual source functions

const rosidl_runtime_c__type_description__TypeSource *
rosgraph_msgs__msg__Service__get_individual_type_description_source(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static const rosidl_runtime_c__type_description__TypeSource source = {
    {rosgraph_msgs__msg__Service__TYPE_NAME, 25, 25},
    {msg_encoding, 3, 3},
    {toplevel_type_raw_source, 388, 388},
  };
  return &source;
}

const rosidl_runtime_c__type_description__TypeSource__Sequence *
rosgraph_msgs__msg__Service__get_type_description_sources(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_runtime_c__type_description__TypeSource sources[5];
  static const rosidl_runtime_c__type_description__TypeSource__Sequence source_sequence = {sources, 5, 5};
  static bool constructed = false;
  if (!constructed) {
    sources[0] = *rosgraph_msgs__msg__Service__get_individual_type_description_source(NULL),
    sources[1] = *builtin_interfaces__msg__Duration__get_individual_type_description_source(NULL);
    sources[2] = *rosgraph_msgs__msg__InterfaceType__get_individual_type_description_source(NULL);
    sources[3] = *rosgraph_msgs__msg__QoSProfile__get_individual_type_description_source(NULL);
    sources[4] = *rosgraph_msgs__msg__TypeHash__get_individual_type_description_source(NULL);
    constructed = true;
  }
  return &source_sequence;
}
