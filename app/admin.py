from django.contrib import admin
from django.urls import reverse
from django.shortcuts import redirect
from django.db import models

# admin.py
from django.contrib import admin
from .models import (
    SiteConfig, FAQ, ScholarshipApplicant,
    Review, Coupon, PreDefinedScholarship
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

    def get_readonly_fields(self, request, v):
        return ["pinecone_updated"]
    
    def upload_to_pinecone(self, request, queryset):
        """Manual action to upload Excel file to Pinecone"""
        from threading import Thread
        from app.embed1 import update_pinecone_embeddings
        
        for obj in queryset:
            if obj.scholarships_db_file:
                print(f"✓ Manual upload triggered for index: {obj.active_dataset_index_name}")
                Thread(target=update_pinecone_embeddings).start()
                self.message_user(request, f"✓ Upload started to index: {obj.active_dataset_index_name}")
            else:
                self.message_user(request, "❌ No Excel file selected. Please upload a file first.")
    
    upload_to_pinecone.short_description = "📤 Manual Upload: Upload Excel data to Pinecone"
    actions = ['upload_to_pinecone']

    fieldsets = (
        ('System Settings', {
            'fields': ('admin_check', 'scholarships_db_file', 'pinecone_updated'),
            'description': 'Basic system configuration'
        }),
        ('Dataset Management', {
            'fields': ('use_default_dataset', 'active_dataset_index_name'),
            'description': 'Manage scholarship dataset indices. Check "Use Default Dataset Index" to use the hardcoded default index "scholarships-index-latest" from stipo54.py. Uncheck to use a custom dataset index.'
        }),
        ('Custom LLM Filter Prompt - Individual Users', {
            'fields': ('use_default_query_filter_individual', 'custom_query_prompt_individual',),
            'description': 'Override the default LLM filter prompt for individual users. Check "Use Default" to use hardcoded default, or uncheck to use custom prompt.',
            'classes': ('collapse',)
        }),
        ('Custom LLM Filter Prompt - Organization Users', {
            'fields': ('use_default_query_filter_organization', 'custom_query_prompt_organization',),
            'description': 'Override the default LLM filter prompt for organization users - förening, klubb, juridisk person. Check "Use Default" to use hardcoded default, or uncheck to use custom prompt.',
            'classes': ('collapse',)
        }),
        ('Custom LLM Reranker Prompt - Individual Users', {
            'fields': ('use_default_reranker_individual', 'custom_reranker_prompt_individual',),
            'description': 'Override the default LLM reranker prompt for individual users. Check "Use Default" to use hardcoded default, or uncheck to use custom prompt.',
            'classes': ('collapse',)
        }),
        ('Custom LLM Reranker Prompt - Organization Users', {
            'fields': ('use_default_reranker_organization', 'custom_reranker_prompt_organization',),
            'description': 'Override the default LLM reranker prompt for organization users. Check "Use Default" to use hardcoded default, or uncheck to use custom prompt.',
            'classes': ('collapse',)
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