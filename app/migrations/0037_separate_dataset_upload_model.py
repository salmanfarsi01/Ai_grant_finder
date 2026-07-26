from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0036_merge_20260706_1609'),
    ]

    operations = [
        migrations.CreateModel(
            name='DatasetUpload',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scholarships_db_file', models.FileField(blank=True, null=True, upload_to='new_scholarships_db.xlsx')),
                ('index_name', models.CharField(default='scholarships-index-latest', max_length=255)),
                ('use_default_dataset', models.BooleanField(default=True)),
                ('active', models.BooleanField(default=True)),
                ('pinecone_updated', models.BooleanField(default=False)),
                ('last_uploaded_at', models.DateTimeField(blank=True, null=True)),
                ('upload_in_progress', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Dataset Upload',
                'verbose_name_plural': 'Dataset Uploads',
                'ordering': ['-updated_at', '-created_at'],
            },
        ),
        migrations.RemoveField(
            model_name='siteconfig',
            name='active_dataset_index_name',
        ),
        migrations.RemoveField(
            model_name='siteconfig',
            name='available_dataset_indices',
        ),
        migrations.RemoveField(
            model_name='siteconfig',
            name='use_default_dataset',
        ),
    ]
