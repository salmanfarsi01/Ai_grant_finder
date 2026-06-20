# Generated migration for Coupon tracking fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0021_siteconfig_llm_reranker_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='coupon',
            name='times_used',
            field=models.PositiveIntegerField(default=0, help_text='Number of times this coupon has been used'),
        ),
        migrations.AddField(
            model_name='coupon',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True, help_text='When the coupon was created'),
        ),
        migrations.AddField(
            model_name='coupon',
            name='last_used',
            field=models.DateTimeField(blank=True, null=True, help_text='Last time this coupon was used'),
        ),
        migrations.AddField(
            model_name='coupon',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Enable/disable this coupon'),
        ),
        migrations.AddField(
            model_name='coupon',
            name='max_uses',
            field=models.PositiveIntegerField(blank=True, null=True, help_text='Maximum times coupon can be used (leave blank for unlimited)'),
        ),
        migrations.AlterField(
            model_name='coupon',
            name='code',
            field=models.CharField(blank=True, default='random_string', max_length=7, null=True, unique=True),
        ),
    ]
