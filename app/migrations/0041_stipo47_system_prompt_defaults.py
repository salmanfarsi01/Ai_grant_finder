from django.db import migrations


STIPO47_SYSTEM_PROMPT = "You always return strict JSON output."


def set_stipo47_defaults(apps, schema_editor):
    LLMPromptConfig = apps.get_model('app', 'LLMPromptConfig')

    for config in LLMPromptConfig.objects.all():
        default_fields = {
            'query_template': 'use_default_query_filter_base',
            'llm_reranker': 'use_default_reranker_base',
            'custom_query_prompt_individual': 'use_default_query_filter_individual',
            'custom_query_prompt_organization': 'use_default_query_filter_organization',
            'custom_reranker_prompt_individual': 'use_default_reranker_individual',
            'custom_reranker_prompt_organization': 'use_default_reranker_organization',
        }
        changed = False
        for field_name, toggle_name in default_fields.items():
            if getattr(config, toggle_name):
                setattr(config, field_name, STIPO47_SYSTEM_PROMPT)
                changed = True
        if changed:
            config.save()


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0040_configuration_models'),
    ]

    operations = [
        migrations.RunPython(set_stipo47_defaults, migrations.RunPython.noop),
    ]
