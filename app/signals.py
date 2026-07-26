import os as _os

from django.dispatch import receiver
from django.db.models.signals import post_save
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone

from .models import ScholarshipApplicant, SiteConfig, DatasetUpload
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

        # Determine language from form_data (default to English)
        language = 'en'
        if isinstance(instance.form_data, dict):
            language = instance.form_data.get('language', 'en')
        language = language.lower() if isinstance(language, str) else 'en'
        language = language if language in ('en', 'sv') else 'en'

        # Use SiteConfig if available for subject/body overrides
        site_config = getattr(settings, 'SITE_CONFIG', None) or SiteConfig.objects.first()
        if site_config:
            subject = site_config.get_report_email_subject(language)
            body = site_config.get_report_email_body(language)
        else:
            if language == 'sv':
                subject = "Din stipendierapport är klar"
                body = "Hej,\n\nDin stipendierapport är bifogad. Granska den bifogade filen för matchade stipendier.\n\nRapportfil: {report_file_name}\n\nVänliga hälsningar,\nStipendieteamet\n"
            else:
                subject = "Your scholarship report is ready"
                body = "Hello,\n\nYour scholarship report is attached. Please review the attached file for the matching scholarships.\n\nReport file: {report_file_name}\n\nBest regards,\nScholarship team\n"

        pdf_path = instance.report_file.path
        report_file_name = _os.path.basename(pdf_path)
        body = body.format(report_file_name=report_file_name, email=instance.email)

        # Build and send the email
        email_msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.EMAIL_HOST_USER,
            to=[instance.email],
        )
        with open(pdf_path, "rb") as pdf:
            email_msg.attach(report_file_name, pdf.read(), "application/pdf")

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

@receiver(post_save, sender=DatasetUpload)
def handle_dataset_upload_save(sender, instance, created, **kwargs):
    """Trigger Pinecone dataset upload when a DatasetUpload record is created or changed."""
    # Skip if this is an internal status update (to prevent recursive signals)
    internal_status_fields = {
        'upload_in_progress',
        'pinecone_updated',
        'upload_status',
        'upload_error_message',
        'upload_progress_percent',
        'upload_rows_uploaded',
        'upload_rows_total',
        'updated_at',
    }
    update_fields = set(kwargs.get('update_fields', []) or [])
    if update_fields and update_fields <= internal_status_fields:
        return

    try:
        current_file = instance.scholarships_db_file
        current_index = instance.get_effective_index_name()

        print(f"\n{'='*60}")
        print(f"📋 DatasetUpload Saved")
        print(f"{'='*60}")
        print(f"  📍 Target Index: {current_index}")
        print(f"  📁 File: {current_file.name if current_file else 'No file'}")
        print(f"  ⏳ Upload Status: {'IN PROGRESS' if instance.upload_in_progress else 'Ready'}")

        if not current_file:
            print(f"  ℹ️  No file attached - skipping upload")
            print(f"{'='*60}\n")
            return

        should_upload = False
        reason = ""
        if created:
            should_upload = True
            reason = "New dataset record created"
        elif update_fields & {'scholarships_db_file', 'index_name', 'use_default_dataset', 'active'}:
            should_upload = True
            reason = "Dataset record updated"

        if should_upload:
            print(f"  ✅ UPLOAD TRIGGERED")
            print(f"  Reason: {reason}")
            print(f"  Status: Starting background upload...")
            print(f"{'='*60}\n")

            DatasetUpload.objects.filter(id=instance.id).update(
                upload_in_progress=True,
                upload_status=DatasetUpload.UPLOAD_STATUS_IN_PROGRESS,
                upload_error_message=None,
                updated_at=timezone.now(),
            )

            thread = Thread(
                target=_upload_with_status_update,
                args=(current_file.path, current_index, instance.id)
            )
            thread.daemon = True
            thread.start()
        else:
            print(f"  ℹ️  No upload needed (no relevant dataset changes)")
            print(f"{'='*60}\n")

    except Exception as e:
        print(f"❌ Error in DatasetUpload signal: {e}")
        print(f"{'='*60}\n")
        raise e


def _upload_with_status_update(file_path, index_name, dataset_id):
    """Upload to Pinecone and update DatasetUpload status when done"""
    try:
        update_pinecone_embeddings(file_path, index_name)

        DatasetUpload.objects.filter(id=dataset_id).update(
            upload_in_progress=False,
            pinecone_updated=True,
            upload_status=DatasetUpload.UPLOAD_STATUS_COMPLETED,
            upload_progress_percent=100,
            upload_rows_uploaded=F('upload_rows_total'),
            last_uploaded_at=timezone.now(),
            updated_at=timezone.now(),
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
        try:
            DatasetUpload.objects.filter(id=dataset_id).update(
                upload_in_progress=False,
                upload_status=DatasetUpload.UPLOAD_STATUS_FAILED,
                upload_error_message=str(e),
                updated_at=timezone.now(),
            )
        except:
            pass



