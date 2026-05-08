# Generated manually for AI Q&A timestamp support
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        # Add duration field to UploadedFile
        migrations.AddField(
            model_name='uploadedfile',
            name='duration',
            field=models.FloatField(
                blank=True, 
                null=True, 
                help_text='Duration in seconds (for audio/video)'
            ),
        ),
        
        # Add timestamp fields to DocumentChunk
        migrations.AddField(
            model_name='documentchunk',
            name='start_time',
            field=models.FloatField(
                blank=True, 
                null=True, 
                help_text='Start time in seconds'
            ),
        ),
        migrations.AddField(
            model_name='documentchunk',
            name='end_time',
            field=models.FloatField(
                blank=True, 
                null=True, 
                help_text='End time in seconds'
            ),
        ),
        
        # Add referenced_timestamp to ChatMessage
        migrations.AddField(
            model_name='chatmessage',
            name='referenced_timestamp',
            field=models.FloatField(
                blank=True, 
                null=True, 
                help_text='Suggested playback time in seconds'
            ),
        ),
        
        # Add index for timestamp queries (performance optimization)
        migrations.AddIndex(
            model_name='documentchunk',
            index=models.Index(
                fields=['file', 'start_time'], 
                name='api_documen_file_id_start_idx'
            ),
        ),
    ]