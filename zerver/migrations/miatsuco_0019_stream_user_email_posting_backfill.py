from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import F


def enable_personal_addresses_for_channels_using_them(
    apps: StateApps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    ChannelEmailAddress = apps.get_model("zerver", "ChannelEmailAddress")
    Stream = apps.get_model("zerver", "Stream")

    channel_ids = ChannelEmailAddress.objects.filter(
        creator_id=F("sender_id"), sender__is_bot=False
    ).values("channel_id")
    Stream.objects.filter(id__in=channel_ids).update(miatsuco_allow_user_email_posting=True)


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "miatsuco_0018_stream_user_email_posting"),
    ]

    operations = [
        migrations.RunPython(
            enable_personal_addresses_for_channels_using_them,
            reverse_code=migrations.RunPython.noop,
            elidable=True,
        ),
    ]
