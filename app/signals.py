import os as _os

from django.dispatch import receiver
from django.db.models.signals import post_save
from django.core.mail import EmailMessage
from django.conf import settings

from .models import ScholarshipApplicant, SiteConfig
from app.embed1 import update_pinecone_embeddings


@receiver(post_save, sender=ScholarshipApplicant)
def handle_application_save(sender, instance, created, **kwargs):
    """
    After all conditions are met (admin_verified, email_verified, paid, report_file exists):
      1. Read the PDF from disk and email it to the customer.
      2. Delete the physical PDF file from disk immediately — no second copy retained.
      3. Clear the report_file field in the DB — keeping form_data and success_count.

    The DB record is intentionally preserved so form input data and scholarship
    results remain queryable. Only the PDF binary is discarded.
    """
    if instance.admin_verified and instance.report_file \
            and instance.email_verified and instance.paid:

        pdf_path = instance.report_file.path

        # --- 1. Build and send the email ---
        subject = "Alegable Scholarships"
        body = ""
        email_msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.EMAIL_HOST_USER,
            to=[instance.email],
        )
        with open(pdf_path, "rb") as pdf:
            email_msg.attach("document.pdf", pdf.read(), "application/pdf")

        print("SENDING FILE>>>")
        email_msg.send()
        print(f"PDF emailed to {instance.email}")

        # --- 2. Delete the physical file from disk immediately ---
        try:
            _os.remove(pdf_path)
            print(f"Physical PDF deleted: {pdf_path}")
        except OSError as exc:
            print(f"Could not delete physical PDF ({pdf_path}): {exc}")

        # --- 3. Clear report_file field in DB (keep the record with form_data) ---
        # Use .update() to avoid re-triggering this post_save signal.
        ScholarshipApplicant.objects.filter(pk=instance.pk).update(
            report_file="",
            pdf_created_at=None,
        )
        print(f"report_file cleared for {instance.email} — form_data and results retained.")


from threading import Thread
from django.db.models import F

@receiver(post_save, sender=SiteConfig)
def handle_site_config_save(sender, instance, created, **kwargs):
    settings.SITE_CONFIG = instance

    # Skip if this is an internal status update (to prevent recursive signals)
    if kwargs.get('update_fields') and len(kwargs.get('update_fields', [])) <= 2:
        if 'upload_in_progress' in kwargs.get('update_fields', []) or 'pinecone_updated' in kwargs.get('update_fields', []):
            return

    try:
        current_file = instance.scholarships_db_file
        current_index = instance.active_dataset_index_name
        previous_index = instance.last_active_dataset_index
        
        print(f"\n{'='*60}")
        print(f"📋 SiteConfig Saved")
        print(f"{'='*60}")
        print(f"  📍 Current Active Index: {current_index}")
        print(f"  📁 File: {current_file.name if current_file else 'No file'}")
        print(f"  ⏳ Upload Status: {'IN PROGRESS' if instance.upload_in_progress else 'Ready'}")
        
        # Prevent duplicate uploads if one is already running
        if instance.upload_in_progress:
            print(f"  ⚠️  Upload already in progress - skipping duplicate upload")
            print(f"{'='*60}\n")
            return
        
        # Only trigger upload if we have a file AND either:
        # 1. The index name changed (user switched datasets)
        # 2. This is a fresh save with file (admin just uploaded)
        index_changed = current_index != previous_index
        
        if not current_file:
            print(f"  ℹ️  No file attached - skipping upload")
            if index_changed:
                # Update the tracking field using direct database update to avoid recursive signal
                SiteConfig.objects.filter(id=instance.id).update(last_active_dataset_index=current_index)
                print(f"  ✅ Index tracking updated: {current_index}")
            print(f"{'='*60}\n")
            return
        
        # File exists - check if we should upload
        should_upload = False
        reason = ""
        
        if index_changed:
            should_upload = True
            reason = f"Index switched: '{previous_index}' → '{current_index}'"
        elif current_file and not created:
            # File was updated but index stayed same - still upload
            should_upload = True
            reason = "New file uploaded (same index)"
        
        if should_upload:
            print(f"  ✅ UPLOAD TRIGGERED")
            print(f"  Reason: {reason}")
            print(f"  🎯 Target Index: {current_index}")
            print(f"  Status: Starting background upload...")
            print(f"{'='*60}\n")
            
            # Use direct database update to avoid recursive signal triggering
            SiteConfig.objects.filter(id=instance.id).update(
                upload_in_progress=True,
                last_active_dataset_index=current_index
            )
            
            # Start upload in background thread
            thread = Thread(
                target=_upload_with_status_update,
                args=(current_file.path, current_index, instance.id)
            )
            thread.daemon = True
            thread.start()
        else:
            print(f"  ℹ️  No upload needed (same index, no file change)")
            print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error in SiteConfig signal: {e}")
        print(f"{'='*60}\n")
        raise e


def _upload_with_status_update(file_path, index_name, config_id):
    """Upload to Pinecone and update SiteConfig status when done"""
    try:
        update_pinecone_embeddings(file_path, index_name)
        
        # Use direct database update to avoid triggering signal again
        SiteConfig.objects.filter(id=config_id).update(
            upload_in_progress=False,
            pinecone_updated=True
        )
        
        print(f"\n{'='*60}")
        print(f"✅ UPLOAD COMPLETE!")
        print(f"{'='*60}")
        print(f"  🎯 Index: {index_name}")
        print(f"  📊 Status: Ready to query")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        print(f"{'='*60}\n")
        # Use direct database update to avoid triggering signal
        try:
            SiteConfig.objects.filter(id=config_id).update(upload_in_progress=False)
        except:
            pass



