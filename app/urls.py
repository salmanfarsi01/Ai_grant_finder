from django.urls import path
from .views import (
    submit_application,
    verify_otp,
    generate_payment_link,
    stripe_payment_webhook,
    generate_data,
    generate_data_playground,
    ReviewView,
    faq_list,
    send_verification_code
)

urlpatterns = [
    path("apply/", submit_application),
    path("<str:email>/send_code/", send_verification_code),
    path("verify_otp/", verify_otp),
    path('<str:email>/<str:method>/pay/', generate_payment_link),
    path('payment_callback/', stripe_payment_webhook),
    path('generate_data/', generate_data),
    path('generate_data_playground/', generate_data_playground),
    path('review/', ReviewView.as_view()),
    path('faqs/', faq_list)
]