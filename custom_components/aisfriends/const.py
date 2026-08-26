"""Constants for the AISFriends integration."""

DOMAIN = "aisfriends"

CONF_USERNAME = "username"
CONF_MMSI_LIST = "mmsi_list"
CONF_RATE_MINUTES = "rate_minutes"
CONF_DEBUG = "debug_logging"

DEFAULT_RATE_MINUTES = 5
MIN_RATE_MINUTES = 1
MAX_RATE_MINUTES = 60

ATTR_NAVIGATIONAL_STATUS = "navigational_status"
ATTR_SPEED_OVER_GROUND = "speed_over_ground_knots"
ATTR_DESTINATION = "destination"
ATTR_ETA = "eta"
ATTR_COURSE = "course_over_ground"
ATTR_HEADING = "true_heading"
ATTR_IMO = "imo"
ATTR_CALL_SIGN = "call_sign"
ATTR_TIMESTAMP = "timestamp"

DIAG_LAST_RAW_RESPONSE = "last_raw_response"
DIAG_LAST_HTTP_STATUS = "last_http_status"
DIAG_LAST_URL = "last_url"
DIAG_LAST_ERROR = "last_error"
DIAG_LAST_SUCCESS_TIME = "last_success_time"
