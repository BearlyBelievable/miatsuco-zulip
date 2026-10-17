from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import OuterRef


def set_default_user_management_groups(
    apps: StateApps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    Realm = apps.get_model("zerver", "Realm")
    NamedUserGroup = apps.get_model("zerver", "NamedUserGroup")

    ADMINISTRATORS_GROUP_NAME = "role:administrators"

    for setting_name in [
        "miatsuco_can_manage_user_activation_group",
        "miatsuco_can_change_user_roles_group",
        "miatsuco_can_edit_user_names_group",
    ]:
        Realm.objects.filter(**{setting_name: None}).update(
            **{
                setting_name: NamedUserGroup.objects.filter(
                    name=ADMINISTRATORS_GROUP_NAME, realm=OuterRef("id"), is_system_group=True
                ).values("pk")
            }
        )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("zerver", "miatsuco_0010_configurable_permissions_add"),
    ]

    operations = [
        migrations.RunPython(
            set_default_user_management_groups,
            elidable=True,
            reverse_code=migrations.RunPython.noop,
        )
    ]
