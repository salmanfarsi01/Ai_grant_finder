from django.contrib import admin
from django.urls import reverse
from django.shortcuts import redirect
from django.db import models

# admin.py
from django.contrib import admin
from .models import (
    SiteConfig, DatasetUpload, FAQ, ScholarshipApplicant,
    Review, Coupon, PreDefinedScholarship, LLMPromptConfig, EmailTemplateConfig
)


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()

    def changelist_view(self, request, extra_context=None):
        obj = SiteConfig.objects.first()
        if obj:
            url = reverse(
                'admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name),
                args=[obj.pk]
            )
            return redirect(url)
        app_label = SiteConfig._meta.app_label
        model_name = SiteConfig._meta.model_name
        print(app_label, model_name)
        return redirect(reverse(f'admin:{app_label}_{model_name}_add'))
        return super().changelist_view(request, extra_context)

    fieldsets = (
        ('System Settings', {
            'fields': ('admin_check',),
            'description': 'Basic system configuration'
        }),
    )


@admin.register(LLMPromptConfig)
class LLMPromptConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Base Prompts', {'fields': ('use_default_query_filter_base', 'query_template', 'use_default_reranker_base', 'llm_reranker')}),
        ('Individual User Prompts', {'fields': ('use_default_query_filter_individual', 'custom_query_prompt_individual', 'use_default_reranker_individual', 'custom_reranker_prompt_individual')}),
        ('Organization User Prompts', {'fields': ('use_default_query_filter_organization', 'custom_query_prompt_organization', 'use_default_reranker_organization', 'custom_reranker_prompt_organization')}),
    )

    def has_add_permission(self, request):
        return not LLMPromptConfig.objects.exists()

    def changelist_view(self, request, extra_context=None):
        obj = LLMPromptConfig.objects.first()
        if obj:
            return redirect(reverse('admin:app_llmpromptconfig_change', args=[obj.pk]))
        return redirect(reverse('admin:app_llmpromptconfig_add'))


@admin.register(EmailTemplateConfig)
class EmailTemplateConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ('OTP Verification Email', {'fields': ('otp_email_subject_en', 'otp_email_body_en', 'otp_email_subject_sv', 'otp_email_body_sv'), 'description': 'Use {otp} and {email} as placeholders.'}),
        ('Final Report Email', {'fields': ('report_email_subject_en', 'report_email_body_en', 'report_email_subject_sv', 'report_email_body_sv'), 'description': 'Use {report_file_name} and {email} as placeholders.'}),
    )

    def has_add_permission(self, request):
        return not EmailTemplateConfig.objects.exists()

    def changelist_view(self, request, extra_context=None):
        obj = EmailTemplateConfig.objects.first()
        if obj:
            return redirect(reverse('admin:app_emailtemplateconfig_change', args=[obj.pk]))
        return redirect(reverse('admin:app_emailtemplateconfig_add'))


@admin.register(DatasetUpload)
class DatasetUploadAdmin(admin.ModelAdmin):
    list_display = (
        'index_name', 'active', 'pinecone_updated', 'upload_status', 'upload_progress_percent', 'upload_rows_uploaded', 'upload_rows_total', 'last_uploaded_at'
    )

    def has_add_permission(self, request):
        return True

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return ['pinecone_updated', 'last_uploaded_at', 'created_at', 'updated_at', 'upload_status', 'upload_progress_percent', 'upload_rows_uploaded', 'upload_rows_total', 'upload_error_message']

    def upload_to_pinecone(self, request, queryset):
        from threading import Thread
        from app.embed1 import update_pinecone_embeddings

        for obj in queryset:
            if obj.scholarships_db_file:
                print(f"✓ Manual upload triggered for index: {obj.get_effective_index_name()}")
                Thread(target=update_pinecone_embeddings, args=(obj.scholarships_db_file.path, obj.get_effective_index_name())).start()
                self.message_user(request, f"✓ Upload started to index: {obj.get_effective_index_name()}")
            else:
                self.message_user(request, "❌ No Excel file selected. Please upload a file first.")

    upload_to_pinecone.short_description = "📤 Manual Upload: Upload Excel data to Pinecone"
    actions = ['upload_to_pinecone']

    fieldsets = (
        ('Dataset Upload', {
            'fields': (
                'scholarships_db_file', 'use_default_dataset', 'index_name', 'active',
                'pinecone_updated', 'upload_status', 'upload_progress_percent', 'upload_rows_uploaded', 'upload_rows_total', 'upload_error_message', 'last_uploaded_at'
            ),
            'description': 'Upload a dataset file and choose the index name used for Pinecone. Mark one dataset as active for queries. Upload status and progress are shown while a background upload runs.'
        }),
    )


@admin.register(FAQ)
class FAQ_Admin(admin.ModelAdmin):
	pass


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    pass


@admin.register(ScholarshipApplicant)
class ScholarshipApplicant(admin.ModelAdmin):
    # def has_add_permission(self, request):
    #     return False

    def get_readonly_fields(self, request, obj=None):
        flag = True
        if obj is None:
            return []
        return [
            field.name for field in obj._meta.fields
            if field.name not in ['admin_verified', 'paid', 'form_data']
        ]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount', 'times_used', 'max_uses', 'is_active', 'last_used', 'usage_percentage')
    list_filter = ('is_active', 'created_at', 'last_used')
    search_fields = ('code',)
    readonly_fields = ('code', 'times_used', 'created_at', 'last_used', 'usage_percentage', 'is_usable_status')
    
    fieldsets = (
        ('Coupon Info', {
            'fields': ('code', 'discount', 'is_active')
        }),
        ('Usage Limits', {
            'fields': ('max_uses', 'times_used', 'usage_percentage')
        }),
        ('Tracking', {
            'fields': ('created_at', 'last_used', 'is_usable_status')
        }),
    )
    
    def usage_percentage(self, obj):
        """Display coupon usage percentage"""
        if obj.max_uses is None:
            return "Unlimited"
        if obj.max_uses == 0:
            return "0%"
        percentage = (obj.times_used / obj.max_uses) * 100
        return f"{percentage:.1f}% ({obj.times_used}/{obj.max_uses})"
    usage_percentage.short_description = "Usage"
    
    def is_usable_status(self, obj):
        """Show if coupon is still usable"""
        if obj.is_usable():
            return "✅ Active & Usable"
        elif not obj.is_active:
            return "🔴 Disabled"
        elif obj.max_uses and obj.times_used >= obj.max_uses:
            return f"🛑 Limit Reached ({obj.times_used}/{obj.max_uses})"
        return "⚠️ Unavailable"
    is_usable_status.short_description = "Status"


@admin.register(PreDefinedScholarship)
class PreDefinedScholarshipAdmin(admin.ModelAdmin):
    list_display = [
        'organization_name'
    ]

    search_fields = ['subject']
    pass