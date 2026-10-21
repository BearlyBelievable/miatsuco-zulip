from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext as _

from zerver.lib.email_mirror_helpers import encode_email_address
from zerver.lib.exceptions import JsonableError
from zerver.lib.miatsuco_channel_email import is_personal_channel_email_address
from zerver.lib.response import json_success
from zerver.lib.streams import access_stream_by_id
from zerver.lib.timestamp import datetime_to_timestamp
from zerver.lib.typed_endpoint import PathOnly, typed_endpoint
from zerver.models import ChannelEmailAddress, Stream, UserProfile


def get_listed_email(
    stream: Stream, channel_email_address: ChannelEmailAddress, user_profile: UserProfile
) -> str | None:
    is_personal = is_personal_channel_email_address(channel_email_address)
    if is_personal and channel_email_address.creator_id != user_profile.id:
        return None
    return encode_email_address(
        stream.name, channel_email_address.email_token, show_sender=not is_personal
    )


@typed_endpoint
def get_channel_email_addresses(
    request: HttpRequest, user_profile: UserProfile, *, stream_id: PathOnly[int]
) -> HttpResponse:
    (stream, _sub) = access_stream_by_id(user_profile, stream_id)

    visible = Q() if user_profile.is_realm_admin else Q(creator=user_profile)
    channel_email_addresses = (
        ChannelEmailAddress.objects.filter(visible, realm=stream.realm, channel=stream)
        .select_related("sender")
        .order_by("id")
    )
    return json_success(
        request,
        data={
            "email_addresses": [
                {
                    "id": channel_email_address.id,
                    "email": get_listed_email(stream, channel_email_address, user_profile),
                    "creator_id": channel_email_address.creator_id,
                    "sender_id": channel_email_address.sender_id,
                    "is_personal": is_personal_channel_email_address(channel_email_address),
                    "date_created": datetime_to_timestamp(channel_email_address.date_created),
                }
                for channel_email_address in channel_email_addresses
            ]
        },
    )


@typed_endpoint
def delete_channel_email_address(
    request: HttpRequest,
    user_profile: UserProfile,
    *,
    stream_id: PathOnly[int],
    email_address_id: PathOnly[int],
) -> HttpResponse:
    (stream, _sub) = access_stream_by_id(user_profile, stream_id)

    channel_email_address = ChannelEmailAddress.objects.filter(
        id=email_address_id, realm=stream.realm, channel=stream
    ).first()
    if channel_email_address is None or not (
        user_profile.is_realm_admin or channel_email_address.creator_id == user_profile.id
    ):
        raise JsonableError(_("No such channel email address."))

    channel_email_address.delete()
    return json_success(request)
