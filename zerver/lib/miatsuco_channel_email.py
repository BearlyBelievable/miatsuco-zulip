from django.db.models import Q
from django.utils.translation import gettext as _

from zerver.lib.exceptions import JsonableError
from zerver.lib.streams import can_administer_accessible_channel
from zerver.models import ChannelEmailAddress, Stream, UserProfile


def is_personal_channel_email_address(channel_email_address: ChannelEmailAddress) -> bool:
    return (
        channel_email_address.creator_id == channel_email_address.sender_id
        and not channel_email_address.sender.is_bot
    )


def delete_channel_email_addresses(*, personal: bool, **filters: object) -> None:
    channel_email_addresses = ChannelEmailAddress.objects.filter(**filters).select_related("sender")
    ChannelEmailAddress.objects.filter(
        id__in=[
            channel_email_address.id
            for channel_email_address in channel_email_addresses
            if is_personal_channel_email_address(channel_email_address) == personal
        ]
    ).delete()


def check_channel_bot_email_allowed(channel: Stream) -> None:
    if not channel.miatsuco_allow_email_posting:
        raise JsonableError(_("Posting by email is not enabled for this channel."))


def check_channel_user_email_allowed(channel: Stream) -> None:
    if not channel.miatsuco_allow_user_email_posting:
        raise JsonableError(_("Messaging this channel by email is not enabled."))


def check_channel_email_allowed(user_profile: UserProfile, channel: Stream) -> None:
    check_channel_bot_email_allowed(channel)

    if not (
        user_profile.is_realm_admin or can_administer_accessible_channel(channel, user_profile)
    ):
        raise JsonableError(_("Only channel administrators can use a channel email address."))


def delete_user_channel_email_addresses(user_profile: UserProfile) -> None:
    ChannelEmailAddress.objects.filter(
        Q(creator=user_profile) | Q(sender=user_profile), realm=user_profile.realm
    ).delete()


def delete_admin_channel_email_addresses(user_profile: UserProfile) -> None:
    delete_channel_email_addresses(personal=False, realm=user_profile.realm, creator=user_profile)


def delete_personal_channel_email_addresses(channel: Stream) -> None:
    delete_channel_email_addresses(personal=True, realm=channel.realm, channel=channel)


def delete_bot_channel_email_addresses(channel: Stream) -> None:
    delete_channel_email_addresses(personal=False, realm=channel.realm, channel=channel)
