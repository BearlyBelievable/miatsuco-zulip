from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "miatsuco_0017_stream_pinned_topic_post_group_not_null"),
    ]

    operations = [
        migrations.AddField(
            model_name="stream",
            name="miatsuco_allow_user_email_posting",
            field=models.BooleanField(db_default=False, default=False),
        ),
    ]
