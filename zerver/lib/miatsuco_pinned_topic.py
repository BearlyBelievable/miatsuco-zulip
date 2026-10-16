from django.db.models import QuerySet
from django.utils.translation import gettext as _

from zerver.lib.exceptions import JsonableError
from zerver.lib.miatsuco_pinned_topic_name import (
    PINNED_TOPIC_PREFIX,
    get_topic_pin_and_bare_name,
    is_pinned_topic,
)
from zerver.lib.streams import can_administer_accessible_channel
from zerver.lib.topic import DB_TOPIC_NAME, RESOLVED_TOPIC_PREFIX, messages_for_topic
from zerver.lib.types import StreamMessageEditRequest
from zerver.models import Message, Stream, UserProfile
from zerver.models.users import is_cross_realm_bot_email


def check_can_manage_pinned_topics(user_profile: UserProfile, stream: Stream) -> None:
    if not (user_profile.is_realm_admin or can_administer_accessible_channel(stream, user_profile)):
        raise JsonableError(
            _("Only channel administrators can pin, unpin, or rename a pinned topic.")
        )


def get_messages_in_topic(stream: Stream, topic_name: str) -> QuerySet[Message]:
    assert stream.recipient_id is not None
    return messages_for_topic(stream.realm_id, stream.recipient_id, topic_name)


def check_not_pinned_and_resolved(topic_name: str) -> None:
    if topic_name.startswith(
        (
            PINNED_TOPIC_PREFIX + RESOLVED_TOPIC_PREFIX,
            RESOLVED_TOPIC_PREFIX + PINNED_TOPIC_PREFIX,
        )
    ):
        raise JsonableError(_("A topic can't be both pinned and resolved."))


def check_pinned_topic_edit(
    user_profile: UserProfile, message_edit_request: StreamMessageEditRequest
) -> None:
    orig_topic_name = message_edit_request.orig_topic_name
    target_topic_name = message_edit_request.target_topic_name

    if message_edit_request.is_stream_edited:
        raise JsonableError(_("Messages can't be moved into or out of a pinned topic."))

    check_can_manage_pinned_topics(user_profile, message_edit_request.orig_stream)
    if message_edit_request.propagate_mode != "change_all":
        raise JsonableError(_("Messages can't be moved into or out of a pinned topic."))

    if (
        orig_topic_name.lower() != target_topic_name.lower()
        and get_messages_in_topic(message_edit_request.orig_stream, target_topic_name).exists()
    ):
        raise JsonableError(_("Messages can't be moved into or out of a pinned topic."))


def check_can_start_pinned_topic(
    user_profile: UserProfile, stream: Stream, topic_name: str
) -> None:
    if not (
        user_profile.is_realm_admin
        or can_administer_accessible_channel(stream, user_profile)
        or get_messages_in_topic(stream, topic_name).exists()
    ):
        raise JsonableError(_("Only channel administrators can start a pinned topic."))


def check_pinned_topic_send(user_profile: UserProfile, stream: Stream, topic_name: str) -> None:
    check_not_pinned_and_resolved(topic_name)
    # The notification bot posts pin and unpin notices in the pinned topic, so
    # cross-realm bots skip the permission checks.
    if is_pinned_topic(topic_name) and not is_cross_realm_bot_email(user_profile.delivery_email):
        check_can_start_pinned_topic(user_profile, stream, topic_name)


def check_pinned_topic_can_be_unpinned(stream: Stream, topic_name: str) -> None:
    unpinned_topic_name = get_topic_pin_and_bare_name(topic_name)[1]
    if get_messages_in_topic(stream, unpinned_topic_name).exists():
        raise JsonableError(
            _(
                "The channel's pinned topic can't be unpinned because the topic"
                " {topic_name} already exists."
            ).format(topic_name=unpinned_topic_name)
        )


def get_other_pinned_topic_names(stream: Stream, excluded_topic_names: list[str]) -> list[str]:
    assert stream.recipient_id is not None
    excluded = {name.lower() for name in excluded_topic_names}
    names = (
        Message.objects.filter(
            realm_id=stream.realm_id,
            recipient_id=stream.recipient_id,
            is_channel_message=True,
            **{f"{DB_TOPIC_NAME}__startswith": PINNED_TOPIC_PREFIX},
        )
        .values_list(DB_TOPIC_NAME, flat=True)
        .distinct()
    )
    return [name for name in names if name.lower() not in excluded]
