"""MiAtSu.Co fork-specific version and feature level constants.

See docs/contributing/miatsuco-fork-conventions.md for the full convention
this module exists to support.
"""

# Human-facing release version of this fork, independent of ZULIP_VERSION.
# Advertised to clients as ``miatsuco_version``. Bump this when cutting a
# fork release; never derive it from or tie it to ZULIP_VERSION.
MIATSUCO_VERSION = "1.0.0-dev"

# Advertised to clients as ``miatsuco_feature_level``. Increase it by one in
# any change that adds or changes something in the fork-specific API.
MIATSUCO_FEATURE_LEVEL = 5
