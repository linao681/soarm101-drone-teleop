// generated from rosidl_generator_c/resource/idl__description.c.em
// with input from rosgraph_msgs:msg/TypeHash.idl
// generated code does not contain a copyright notice

#include "rosgraph_msgs/msg/detail/type_hash__functions.h"

ROSIDL_GENERATOR_C_PUBLIC_rosgraph_msgs
const rosidl_type_hash_t *
rosgraph_msgs__msg__TypeHash__get_type_hash(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_type_hash_t hash = {1, {
      0xb5, 0x72, 0x48, 0xb9, 0xd4, 0xea, 0x09, 0x64,
      0xbd, 0x58, 0x3c, 0x53, 0xae, 0x3b, 0x94, 0x35,
      0x4e, 0x59, 0x9b, 0x81, 0x83, 0xa1, 0x35, 0xaf,
      0x48, 0x82, 0x62, 0x87, 0xbe, 0xf3, 0xc1, 0xf6,
    }};
  return &hash;
}

#include <assert.h>
#include <string.h>

// Include directives for referenced types

// Hashes for external referenced types
#ifndef NDEBUG
#endif

static char rosgraph_msgs__msg__TypeHash__TYPE_NAME[] = "rosgraph_msgs/msg/TypeHash";

// Define type names, field names, and default values
static char rosgraph_msgs__msg__TypeHash__FIELD_NAME__version[] = "version";
static char rosgraph_msgs__msg__TypeHash__DEFAULT_VALUE__version[] = "1";
static char rosgraph_msgs__msg__TypeHash__FIELD_NAME__value[] = "value";

static rosidl_runtime_c__type_description__Field rosgraph_msgs__msg__TypeHash__FIELDS[] = {
  {
    {rosgraph_msgs__msg__TypeHash__FIELD_NAME__version, 7, 7},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_UINT8,
      0,
      0,
      {NULL, 0, 0},
    },
    {rosgraph_msgs__msg__TypeHash__DEFAULT_VALUE__version, 1, 1},
  },
  {
    {rosgraph_msgs__msg__TypeHash__FIELD_NAME__value, 5, 5},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_UINT8_ARRAY,
      32,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
};

const rosidl_runtime_c__type_description__TypeDescription *
rosgraph_msgs__msg__TypeHash__get_type_description(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static bool constructed = false;
  static const rosidl_runtime_c__type_description__TypeDescription description = {
    {
      {rosgraph_msgs__msg__TypeHash__TYPE_NAME, 26, 26},
      {rosgraph_msgs__msg__TypeHash__FIELDS, 2, 2},
    },
    {NULL, 0, 0},
  };
  if (!constructed) {
    constructed = true;
  }
  return &description;
}

static char toplevel_type_raw_source[] =
  "# RIHS spec version\n"
  "uint8 version 1\n"
  "# ROSIDL_TYPE_HASH_SIZE == 32\n"
  "uint8[32] value";

static char msg_encoding[] = "msg";

// Define all individual source functions

const rosidl_runtime_c__type_description__TypeSource *
rosgraph_msgs__msg__TypeHash__get_individual_type_description_source(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static const rosidl_runtime_c__type_description__TypeSource source = {
    {rosgraph_msgs__msg__TypeHash__TYPE_NAME, 26, 26},
    {msg_encoding, 3, 3},
    {toplevel_type_raw_source, 82, 82},
  };
  return &source;
}

const rosidl_runtime_c__type_description__TypeSource__Sequence *
rosgraph_msgs__msg__TypeHash__get_type_description_sources(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_runtime_c__type_description__TypeSource sources[1];
  static const rosidl_runtime_c__type_description__TypeSource__Sequence source_sequence = {sources, 1, 1};
  static bool constructed = false;
  if (!constructed) {
    sources[0] = *rosgraph_msgs__msg__TypeHash__get_individual_type_description_source(NULL),
    constructed = true;
  }
  return &source_sequence;
}
