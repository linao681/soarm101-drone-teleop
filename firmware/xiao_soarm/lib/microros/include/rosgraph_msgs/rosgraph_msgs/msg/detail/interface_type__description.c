// generated from rosidl_generator_c/resource/idl__description.c.em
// with input from rosgraph_msgs:msg/InterfaceType.idl
// generated code does not contain a copyright notice

#include "rosgraph_msgs/msg/detail/interface_type__functions.h"

ROSIDL_GENERATOR_C_PUBLIC_rosgraph_msgs
const rosidl_type_hash_t *
rosgraph_msgs__msg__InterfaceType__get_type_hash(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_type_hash_t hash = {1, {
      0x08, 0xe2, 0x22, 0xa0, 0xb6, 0x95, 0x0d, 0x27,
      0x5c, 0x45, 0xc2, 0x92, 0x4b, 0x6b, 0xb6, 0xb7,
      0x9b, 0x7f, 0xde, 0xde, 0x9c, 0x90, 0xcd, 0xf5,
      0xd6, 0x95, 0x2d, 0xc6, 0xf1, 0x97, 0x91, 0x6c,
    }};
  return &hash;
}

#include <assert.h>
#include <string.h>

// Include directives for referenced types
#include "rosgraph_msgs/msg/detail/type_hash__functions.h"

// Hashes for external referenced types
#ifndef NDEBUG
static const rosidl_type_hash_t rosgraph_msgs__msg__TypeHash__EXPECTED_HASH = {1, {
    0xb5, 0x72, 0x48, 0xb9, 0xd4, 0xea, 0x09, 0x64,
    0xbd, 0x58, 0x3c, 0x53, 0xae, 0x3b, 0x94, 0x35,
    0x4e, 0x59, 0x9b, 0x81, 0x83, 0xa1, 0x35, 0xaf,
    0x48, 0x82, 0x62, 0x87, 0xbe, 0xf3, 0xc1, 0xf6,
  }};
#endif

static char rosgraph_msgs__msg__InterfaceType__TYPE_NAME[] = "rosgraph_msgs/msg/InterfaceType";
static char rosgraph_msgs__msg__TypeHash__TYPE_NAME[] = "rosgraph_msgs/msg/TypeHash";

// Define type names, field names, and default values
static char rosgraph_msgs__msg__InterfaceType__FIELD_NAME__name[] = "name";
static char rosgraph_msgs__msg__InterfaceType__FIELD_NAME__hash[] = "hash";

static rosidl_runtime_c__type_description__Field rosgraph_msgs__msg__InterfaceType__FIELDS[] = {
  {
    {rosgraph_msgs__msg__InterfaceType__FIELD_NAME__name, 4, 4},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_STRING,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
  {
    {rosgraph_msgs__msg__InterfaceType__FIELD_NAME__hash, 4, 4},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {rosgraph_msgs__msg__TypeHash__TYPE_NAME, 26, 26},
    },
    {NULL, 0, 0},
  },
};

static rosidl_runtime_c__type_description__IndividualTypeDescription rosgraph_msgs__msg__InterfaceType__REFERENCED_TYPE_DESCRIPTIONS[] = {
  {
    {rosgraph_msgs__msg__TypeHash__TYPE_NAME, 26, 26},
    {NULL, 0, 0},
  },
};

const rosidl_runtime_c__type_description__TypeDescription *
rosgraph_msgs__msg__InterfaceType__get_type_description(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static bool constructed = false;
  static const rosidl_runtime_c__type_description__TypeDescription description = {
    {
      {rosgraph_msgs__msg__InterfaceType__TYPE_NAME, 31, 31},
      {rosgraph_msgs__msg__InterfaceType__FIELDS, 2, 2},
    },
    {rosgraph_msgs__msg__InterfaceType__REFERENCED_TYPE_DESCRIPTIONS, 1, 1},
  };
  if (!constructed) {
    assert(0 == memcmp(&rosgraph_msgs__msg__TypeHash__EXPECTED_HASH, rosgraph_msgs__msg__TypeHash__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[0].fields = rosgraph_msgs__msg__TypeHash__get_type_description(NULL)->type_description.fields;
    constructed = true;
  }
  return &description;
}

static char toplevel_type_raw_source[] =
  "# Represent a type of a ROS Graph Interface\n"
  "\n"
  "# The plaintext namespaced name of the type - e.g. sensor_msgs/Image\n"
  "string name\n"
  "\n"
  "# The hash uniquely identifies the exact structure of the type,\n"
  "# the definition of which may change between package version\n"
  "TypeHash hash";

static char msg_encoding[] = "msg";

// Define all individual source functions

const rosidl_runtime_c__type_description__TypeSource *
rosgraph_msgs__msg__InterfaceType__get_individual_type_description_source(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static const rosidl_runtime_c__type_description__TypeSource source = {
    {rosgraph_msgs__msg__InterfaceType__TYPE_NAME, 31, 31},
    {msg_encoding, 3, 3},
    {toplevel_type_raw_source, 266, 266},
  };
  return &source;
}

const rosidl_runtime_c__type_description__TypeSource__Sequence *
rosgraph_msgs__msg__InterfaceType__get_type_description_sources(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_runtime_c__type_description__TypeSource sources[2];
  static const rosidl_runtime_c__type_description__TypeSource__Sequence source_sequence = {sources, 2, 2};
  static bool constructed = false;
  if (!constructed) {
    sources[0] = *rosgraph_msgs__msg__InterfaceType__get_individual_type_description_source(NULL),
    sources[1] = *rosgraph_msgs__msg__TypeHash__get_individual_type_description_source(NULL);
    constructed = true;
  }
  return &source_sequence;
}
