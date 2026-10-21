from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "miatsuco_0019_stream_user_email_posting_backfill"),
    ]

    operations = [
        migrations.AddField(
            model_name="stream",
            name="miatsuco_allow_email_posting",
            field=models.BooleanField(db_default=False, default=False),
        ),
    ]
