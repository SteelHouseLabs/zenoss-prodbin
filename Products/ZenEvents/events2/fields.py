###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

class EventField:
    UUID = 'uuid'
    CREATED_TIME = 'created_time'
    FINGERPRINT = 'fingerprint'
    EVENT_CLASS = 'event_class'
    EVENT_CLASS_KEY = 'event_class_key'
    EVENT_CLASS_MAPPING_UUID = 'event_class_mapping_uuid'
    ACTOR = 'actor'
    SUMMARY = 'summary'
    MESSAGE = 'message'
    SEVERITY = 'severity'
    EVENT_KEY = 'event_key'
    EVENT_GROUP = 'event_group'
    AGENT = 'agent'
    SYSLOG_PRIORITY = 'syslog_priority'
    SYSLOG_FACILITY = 'syslog_facility'
    NT_EVENT_CODE = 'nt_event_code'
    MONITOR = 'monitor'
    DETAILS = 'details'
    TAGS = 'tags'

    class Actor:
        ELEMENT_TYPE_ID = 'element_type_id'
        ELEMENT_IDENTIFIER = 'element_identifier'
        ELEMENT_UUID = 'element_uuid'
        ELEMENT_SUB_TYPE_ID = 'element_sub_type_id'
        ELEMENT_SUB_IDENTIFIER = 'element_sub_identifier'
        ELEMENT_SUB_UUID = 'element_sub_uuid'

    class Detail:
        NAME = 'name'
        VALUE = 'value'

    class Tag:
        TYPE = 'type'
        UUID = 'uuid'

class EventSummaryField:
    UUID = 'uuid'
    OCCURRENCE = 'occurrence'
    STATUS = 'status'
    FIRST_SEEN_TIME = 'first_seen_time'
    STATUS_CHANGE_TIME = 'status_change_time'
    LAST_SEEN_TIME = 'last_seen_time'
    COUNT = 'count'
    CURRENT_USER_UUID = 'current_user_uuid'
    CURRENT_USER_NAME = 'current_user_name'
    CLEARED_BY_EVENT_UUID = 'cleared_by_event_uuid'
    NOTES = 'notes'
    AUDIT_LOG = 'audit_log'

class ZepRawEventField:
    RAW_EVENT = 'raw_event'
    INDEX = 'index'
    CLEAR_EVENT_CLASS = 'clear_event_class'
    STATUS = 'status'
    TAGS = 'tags'