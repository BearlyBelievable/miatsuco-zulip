from django.db.models import Q
from django.utils.translation import gettext as _

from zerver.lib.exceptions import JsonableError
from zerver.models import ChannelEmailAddress, Stream, UserProfile


def is_personal_channel_email_address(channel_email_address: ChannelEmailAddress) -> bool:
    return (
        channel_email_address.creator_id == channel_email_address.sender_id
        and not channel_email_address.sender.is_bot
    )


def check_channel_user_email_allowed(channel: Stream) -> None:
    if not channel.miatsuco_allow_user_email_posting:
        raise JsonableError(_("Messaging this channel by email is not enabled."))


def delete_user_channel_email_addresses(user_profile: UserProfile) -> None:
    ChannelEmailAddress.objects.filter(
        Q(creator=user_profile) | Q(sender=user_profile), realm=user_profile.realm
    ).delete()


def delete_personal_channel_email_addresses(channel: Stream) -> None:
    channel_email_addresses = ChannelEmailAddress.objects.filter(
        realm=channel.realm, channel=channel
    ).select_related("sender")
    ChannelEmailAddress.objects.filter(
        id__in=[
            channel_email_address.id
            for channel_email_address in channel_email_addresses
            if is_personal_channel_email_address(channel_email_address)
        ]
    ).delete()
