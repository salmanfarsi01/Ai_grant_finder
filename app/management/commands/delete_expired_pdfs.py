"""
Management command: delete_expired_pdfs
=======================================
Deletes any PDF report files that have been sitting on disk for more than
24 hours since they were generated (pdf_created_at).

This is a safety net.  Under normal operation the PDF is deleted immediately
after it is emailed to the customer by the post_save signal in signals.py.
This command catches edge cases where the signal failed or the file was not
cleaned up for any other reason.

Usage (run manually or via cron/Celery beat):
    python manage.py delete_expired_pdfs

Recommended cron (every hour):
    0 * * * * cd /path/to/project && python manage.py delete_expired_pdfs >> /var/log/delete_pdfs.log 2>&1
"""

import os

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from app.models import ScholarshipApplicant


PDF_LIFETIME_HOURS = 24


class Command(BaseCommand):
    help = (
        f"Delete PDF report files older than {PDF_LIFETIME_HOURS} hours. "
        "Keeps form_data and scholarship results in the database."
    )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=PDF_LIFETIME_HOURS)

        # Find applicants whose PDF has been on disk for > 24 hours
        expired = ScholarshipApplicant.objects.filter(
            pdf_created_at__lt=cutoff,
            report_file__isnull=False,
        ).exclude(report_file="")

        count_deleted = 0
        count_errors = 0

        for applicant in expired:
            pdf_field = applicant.report_file

            # Build the physical path before clearing the field
            try:
                pdf_path = pdf_field.path
            except (ValueError, NotImplementedError):
                # Field is empty/missing — just clear the timestamp
                ScholarshipApplicant.objects.filter(pk=applicant.pk).update(
                    pdf_created_at=None,
                )
                continue

            # Delete the physical file
            deleted_file = False
            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                    deleted_file = True
                    self.stdout.write(
                        self.style.WARNING(f"Deleted expired PDF: {pdf_path}")
                    )
                except OSError as exc:
                    count_errors += 1
                    self.stderr.write(
                        f"Could not delete {pdf_path}: {exc}"
                    )
            else:
                # File already gone from disk — still clean the DB field
                deleted_file = True
                self.stdout.write(
                    self.style.WARNING(
                        f"PDF file already missing from disk for {applicant.email}: {pdf_path}"
                    )
                )

            if deleted_file:
                # Clear the report_file field but preserve form_data and success_count
                ScholarshipApplicant.objects.filter(pk=applicant.pk).update(
                    report_file="",
                    pdf_created_at=None,
                )
                count_deleted += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Expired PDFs cleaned: {count_deleted}  |  Errors: {count_errors}"
            )
        )
