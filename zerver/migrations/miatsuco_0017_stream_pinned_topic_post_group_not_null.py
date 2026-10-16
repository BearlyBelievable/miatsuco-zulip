import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "miatsuco_0016_stream_pinned_topic_post_group_defaults"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stream",
            name="miatsuco_can_post_in_pinned_topic_group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="+",
                to="zerver.usergroup",
            ),
        ),
    ]
