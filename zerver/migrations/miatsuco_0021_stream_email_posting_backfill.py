from django.conf import settings
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import OuterRef, Subquery


def enable_bot_addresses_for_channels_using_the_email_gateway(
    apps: StateApps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    UserProfile = apps.get_model("zerver", "UserProfile")
    Stream = apps.get_model("zerver", "Stream")
    Message = apps.get_model("zerver", "Message")

    gateway_bot = UserProfile.objects.filter(email__iexact=settings.EMAIL_GATEWAY_BOT).first()
    if gateway_bot is None:
        return

    recipient_ids = Message.objects.filter(sender_id=gateway_bot.id).values("recipient_id")
    Stream.objects.filter(recipient_id__in=recipient_ids).update(miatsuco_allow_email_posting=True)


def detach_legacy_bot_addresses_from_creators(
    apps: StateApps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    ChannelEmailAddress = apps.get_model("zerver", "ChannelEmailAddress")
    Stream = apps.get_model("zerver", "Stream")

    channel_date_created = Stream.objects.filter(id=OuterRef("channel_id")).values("date_created")
    ChannelEmailAddress.objects.filter(date_created=Subquery(channel_date_created)).update(
        creator=None
    )


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "miatsuco_0020_stream_email_posting"),
    ]

    operations = [
        migrations.RunPython(
            enable_bot_addresses_for_channels_using_the_email_gateway,
            reverse_code=migrations.RunPython.noop,
            elidable=True,
        ),
        migrations.RunPython(
            detach_legacy_bot_addresses_from_creators,
            reverse_code=migrations.RunPython.noop,
            elidable=True,
        ),
    ]
