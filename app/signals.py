from django.dispatch import receiver
from django.db.models.signals import post_save
from django.core.mail import EmailMessage
from django.conf import settings

from .models import ScholarshipApplicant, SiteConfig
from app.embed1 import update_pinecone_embeddings


@receiver(post_save, sender=ScholarshipApplicant)
def handle_application_save(sender, instance, created, **kwargs):
    if instance.admin_verified and instance.report_file\
            and instance.email_verified and instance.paid:

        subject = "Alegable Scholarships"
        body = ""
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.EMAIL_HOST_USER,
            to=[instance.email],
        )
        pdf_path = instance.report_file.path
        with open(pdf_path, "rb") as pdf:
            email.attach("document.pdf", pdf.read(), "application/pdf")

        # Send the email
        print("SENDING FILE>>>")
        print("SENDING FILE>>>")
        email.send()
        instance.delete()
    pass

from threading import Thread

@receiver(post_save, sender=SiteConfig)
def handle_site_config_save(sender, instance, created, **kwargs):
    settings.SITE_CONFIG = instance

    try:
        # Only upload if scholarships_db_file was EXPLICITLY uploaded in THIS request
        # Check if there's a POST request indicating file upload
        from django.core.files.storage import default_storage
        
        current_file = instance.scholarships_db_file
        
        # Simple check: Only trigger upload if file exists AND 
        # this is likely a fresh upload (file size recent change would indicate upload)
        # For now, NEVER auto-trigger - only manual trigger via admin action
        
        print(f"✓ SiteConfig saved. Index: {instance.active_dataset_index_name}")
        print(f"  No automatic upload triggered. To upload data:")
        print(f"  1. Select Excel file in 'Scholarships DB File' field")
        print(f"  2. Click Save")
        
    except Exception as e:
        print(f"Error in SiteConfig signal: {e}")
        raise e

