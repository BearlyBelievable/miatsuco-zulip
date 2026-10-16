PINNED_TOPIC_PREFIX = "📌 "


def is_pinned_topic(topic_name: str) -> bool:
    return topic_name.startswith(PINNED_TOPIC_PREFIX)


def get_topic_pin_and_bare_name(stored_name: str) -> tuple[bool, str]:
    if is_pinned_topic(stored_name):
        return (True, stored_name.removeprefix(PINNED_TOPIC_PREFIX))

    return (False, stored_name)


def topic_was_pinned(
    old_topic_name: str, target_topic_name: str, pre_truncation_target_topic_name: str
) -> bool:
    return (
        is_pinned_topic(target_topic_name)
        and not is_pinned_topic(old_topic_name)
        and pre_truncation_target_topic_name.removeprefix(PINNED_TOPIC_PREFIX) == old_topic_name
    )


def topic_was_unpinned(old_topic_name: str, target_topic_name: str) -> bool:
    old_topic_pinned, old_bare_name = get_topic_pin_and_bare_name(old_topic_name)
    return old_topic_pinned and old_bare_name == target_topic_name


def topic_pin_toggled(topic: str, prev_topic: str) -> bool:
    if is_pinned_topic(topic) and topic.removeprefix(PINNED_TOPIC_PREFIX) == prev_topic:
        return True
    return topic_was_unpinned(prev_topic, topic)
