from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import Max, Min, OuterRef

BATCH_SIZE = 1000


def set_default_pinned_topic_post_group(
    apps: StateApps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    Stream = apps.get_model("zerver", "Stream")
    NamedUserGroup = apps.get_model("zerver", "NamedUserGroup")

    unset_streams = Stream.objects.filter(miatsuco_can_post_in_pinned_topic_group=None)
    bounds = unset_streams.aggregate(Min("id"), Max("id"))
    if bounds["id__min"] is None:
        return

    lower_bound = bounds["id__min"]
    while lower_bound <= bounds["id__max"]:
        upper_bound = lower_bound + BATCH_SIZE - 1
        unset_streams.filter(id__range=(lower_bound, upper_bound)).update(
            miatsuco_can_post_in_pinned_topic_group=NamedUserGroup.objects.filter(
                name="role:everyone",
                realm_for_sharding=OuterRef("realm_id"),
                is_system_group=True,
            ).values("pk")
        )
        lower_bound += BATCH_SIZE


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("zerver", "miatsuco_0015_stream_pinned_topic_post_group_add"),
    ]

    operations = [
        migrations.RunPython(
            set_default_pinned_topic_post_group,
            elidable=True,
            reverse_code=migrations.RunPython.noop,
        )
    ]
