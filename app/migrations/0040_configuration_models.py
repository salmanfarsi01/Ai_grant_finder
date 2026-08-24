from django.db import migrations, models


def copy_configuration(apps, schema_editor):
    SiteConfig = apps.get_model('app', 'SiteConfig')
    LLMPromptConfig = apps.get_model('app', 'LLMPromptConfig')
    EmailTemplateConfig = apps.get_model('app', 'EmailTemplateConfig')

    site_config = SiteConfig.objects.first()
    prompt_config = LLMPromptConfig.objects.create()
    email_config = EmailTemplateConfig.objects.create()

    if not site_config:
        return

    prompt_fields = (
        'query_template', 'llm_reranker',
        'custom_query_prompt_individual', 'custom_query_prompt_organization',
        'custom_reranker_prompt_individual', 'custom_reranker_prompt_organization',
        'use_default_query_filter_base', 'use_default_query_filter_individual',
        'use_default_query_filter_organization', 'use_default_reranker_base',
        'use_default_reranker_individual', 'use_default_reranker_organization',
    )
    for field_name in prompt_fields:
        setattr(prompt_config, field_name, getattr(site_config, field_name))
    prompt_config.save()

    email_fields = (
        'otp_email_subject_en', 'otp_email_body_en',
        'otp_email_subject_sv', 'otp_email_body_sv',
        'report_email_subject_en', 'report_email_body_en',
        'report_email_subject_sv', 'report_email_body_sv',
    )
    for field_name in email_fields:
        setattr(email_config, field_name, getattr(site_config, field_name))
    email_config.save()


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0039_datasetupload_upload_error_message_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LLMPromptConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query_template', models.TextField(blank=True, default='You always return strict JSON output.', help_text='Default: You always return strict JSON output.', verbose_name='LLM filter system prompt')),
                ('llm_reranker', models.TextField(blank=True, default='You always return strict JSON output.', help_text='Default: You always return strict JSON output.', verbose_name='LLM reranker system prompt')),
                ('custom_query_prompt_individual', models.TextField(blank=True, default='', help_text='Leave blank to use the built-in individual filter prompt.', verbose_name='Individual filter prompt')),
                ('custom_query_prompt_organization', models.TextField(blank=True, default='', help_text='Leave blank to use the built-in organization filter prompt.', verbose_name='Organization filter prompt')),
                ('custom_reranker_prompt_individual', models.TextField(blank=True, default='', help_text='Leave blank to use the built-in individual reranker prompt.', verbose_name='Individual reranker prompt')),
                ('custom_reranker_prompt_organization', models.TextField(blank=True, default='', help_text='Leave blank to use the built-in organization reranker prompt.', verbose_name='Organization reranker prompt')),
                ('use_default_query_filter_base', models.BooleanField(default=True, verbose_name='Use built-in base filter prompt')),
                ('use_default_query_filter_individual', models.BooleanField(default=True, verbose_name='Use built-in individual filter prompt')),
                ('use_default_query_filter_organization', models.BooleanField(default=True, verbose_name='Use built-in organization filter prompt')),
                ('use_default_reranker_base', models.BooleanField(default=True, verbose_name='Use built-in base reranker prompt')),
                ('use_default_reranker_individual', models.BooleanField(default=True, verbose_name='Use built-in individual reranker prompt')),
                ('use_default_reranker_organization', models.BooleanField(default=True, verbose_name='Use built-in organization reranker prompt')),
            ],
            options={'verbose_name': 'LLM Prompt Configuration', 'verbose_name_plural': 'LLM Prompt Configuration'},
        ),
        migrations.CreateModel(
            name='EmailTemplateConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('otp_email_subject_en', models.CharField(default='Your scholarship OTP code', max_length=255)),
                ('otp_email_body_en', models.TextField(default='Hello,\n\nUse this OTP code to continue your scholarship search:\n\n{otp}\n\nThank you.\n')),
                ('otp_email_subject_sv', models.CharField(default='Din OTP-kod för stipendiesökning', max_length=255)),
                ('otp_email_body_sv', models.TextField(default='Hej,\n\nAnvänd denna OTP-kod för att fortsätta din stipendiesökning:\n\n{otp}\n\nTack.\n')),
                ('report_email_subject_en', models.CharField(default='Your scholarship report is ready', max_length=255)),
                ('report_email_body_en', models.TextField(default='Hello,\n\nYour scholarship report is attached. Please review the attached file for the matching scholarships.\n\nReport file: {report_file_name}\n\nBest regards,\nScholarship team\n')),
                ('report_email_subject_sv', models.CharField(default='Din stipendierapport är klar', max_length=255)),
                ('report_email_body_sv', models.TextField(default='Hej,\n\nDin stipendierapport är bifogad. Granska den bifogade filen för matchade stipendier.\n\nRapportfil: {report_file_name}\n\nVänliga hälsningar,\nStipendieteamet\n')),
            ],
            options={'verbose_name': 'Email Template Configuration', 'verbose_name_plural': 'Email Template Configuration'},
        ),
        migrations.RunPython(copy_configuration, migrations.RunPython.noop),
        migrations.RemoveField(model_name='siteconfig', name='query_template'),
        migrations.RemoveField(model_name='siteconfig', name='llm_reranker'),
        migrations.RemoveField(model_name='siteconfig', name='custom_query_prompt_individual'),
        migrations.RemoveField(model_name='siteconfig', name='custom_query_prompt_organization'),
        migrations.RemoveField(model_name='siteconfig', name='custom_reranker_prompt_individual'),
        migrations.RemoveField(model_name='siteconfig', name='custom_reranker_prompt_organization'),
        migrations.RemoveField(model_name='siteconfig', name='use_default_query_filter_base'),
        migrations.RemoveField(model_name='siteconfig', name='use_default_query_filter_individual'),
        migrations.RemoveField(model_name='siteconfig', name='use_default_query_filter_organization'),
        migrations.RemoveField(model_name='siteconfig', name='use_default_reranker_base'),
        migrations.RemoveField(model_name='siteconfig', name='use_default_reranker_individual'),
        migrations.RemoveField(model_name='siteconfig', name='use_default_reranker_organization'),
        migrations.RemoveField(model_name='siteconfig', name='otp_email_subject_en'),
        migrations.RemoveField(model_name='siteconfig', name='otp_email_body_en'),
        migrations.RemoveField(model_name='siteconfig', name='otp_email_subject_sv'),
        migrations.RemoveField(model_name='siteconfig', name='otp_email_body_sv'),
        migrations.RemoveField(model_name='siteconfig', name='report_email_subject_en'),
        migrations.RemoveField(model_name='siteconfig', name='report_email_body_en'),
        migrations.RemoveField(model_name='siteconfig', name='report_email_subject_sv'),
        migrations.RemoveField(model_name='siteconfig', name='report_email_body_sv'),
    ]
