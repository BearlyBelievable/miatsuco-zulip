from django.db.models import Q

from zerver.models import ChannelEmailAddress, UserProfile


def delete_user_channel_email_addresses(user_profile: UserProfile) -> None:
    ChannelEmailAddress.objects.filter(
        Q(creator=user_profile) | Q(sender=user_profile), realm=user_profile.realm
    ).delete()
