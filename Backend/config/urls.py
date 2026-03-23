from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from patients.views import PatientViewSet
from visits.views import VisitViewSet
from assessments.views import (
    AssessmentViewSet, 
    AssessmentFileViewSet,
    LabMeasurementViewSet,
    VitalMeasurementViewSet,
    AnalysisResultViewSet
)
from rest_framework_simplejwt.views import TokenRefreshView

from users.views import (
    SignupView,
    ApproveSignupView,
    RejectSignupView,
    CustomLoginView,
    PendingSignupRequestsView,
    MeView,
)
from django.conf import settings
from django.conf.urls.static import static


router = DefaultRouter()
router.register(r"patients", PatientViewSet)
router.register(r"visits", VisitViewSet)
router.register(r"assessments", AssessmentViewSet)
router.register(r"assessmentfiles", AssessmentFileViewSet)
router.register(r"labmeasurements", LabMeasurementViewSet)
router.register(r"vitalmeasurements", VitalMeasurementViewSet)
router.register(r"analysisresults", AnalysisResultViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),

    # ================= AUTH =================
    path("api/auth/signup/", SignupView.as_view()),
    path("api/auth/login/", CustomLoginView.as_view()),
    path("api/auth/refresh/", TokenRefreshView.as_view()),
    path("api/auth/pending/", PendingSignupRequestsView.as_view()),
    path("api/auth/approve/<int:request_id>/", ApproveSignupView.as_view()),
    path("api/auth/reject/<int:request_id>/", RejectSignupView.as_view()),

    path("api/me/", MeView.as_view()),

    # ================= APP ROUTES =================
    path("api/", include(router.urls)),
    path("api/assessments/", include("assessments.urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
