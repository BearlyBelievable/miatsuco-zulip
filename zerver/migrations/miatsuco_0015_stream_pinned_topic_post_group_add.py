import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "miatsuco_0014_stream_retain_topics"),
    ]

    operations = [
        migrations.AddField(
            model_name="stream",
            name="miatsuco_can_post_in_pinned_topic_group",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="+",
                to="zerver.usergroup",
            ),
        ),
    ]
