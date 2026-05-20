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

        Thread(target=update_pinecone_embeddings).start()
        # instance.pinecone_updated=True
        # instance.save()
        pass
    except Exception as e:
        raise e
        print(e)

