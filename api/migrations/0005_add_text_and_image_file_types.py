from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_alter_uploadedfile_uploaded_by"),
    ]

    operations = [
        migrations.AlterField(
            model_name="uploadedfile",
            name="file_type",
            field=models.CharField(
                choices=[
                    ("pdf", "PDF Document"),
                    ("text", "Text Document"),
                    ("audio", "Audio File"),
                    ("image", "Image File"),
                    ("video", "Video File"),
                ],
                max_length=10,
            ),
        ),
    ]