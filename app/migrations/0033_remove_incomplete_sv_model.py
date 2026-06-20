# Generated migration - removes incomplete PreDefinedScholarship_Sv model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0032_alter_predefinedscholarship_subject'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PreDefinedScholarship_Sv',
        ),
    ]
