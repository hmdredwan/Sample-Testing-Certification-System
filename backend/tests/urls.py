from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('types/', views.PublicTestTypesView.as_view(), name='public-test-types'),
    path('certificates/verify/<str:code>/', views.PublicVerifyCertificateView.as_view(), name='public-verify-certificate'),
    path('certificates/download/<str:code>/', views.DownloadCertificatePDFView.as_view(), name='download-certificate-pdf'),

    # User test requests
    path('requests/', views.UserTestRequestListView.as_view(), name='user-test-requests'),
    path('requests/create/', views.CreateTestRequestView.as_view(), name='create-test-request'),
    path('requests/<uuid:pk>/', views.UserTestRequestDetailView.as_view(), name='user-test-detail'),

    # Sample barcode / QR label & custody
    path('requests/<uuid:pk>/sample-label/', views.SampleLabelView.as_view(), name='sample-label'),
    path('requests/<uuid:pk>/custody/log/', views.CreateCustodyLogView.as_view(), name='create-custody-log'),
    path('requests/<uuid:pk>/custody/history/', views.SampleCustodyHistoryView.as_view(), name='custody-history'),

    # Certificates
    path('requests/<uuid:pk>/certificate/generate/', views.GenerateCertificateView.as_view(), name='generate-certificate'),

    # Lab Technician views
    path('technician/requests/', views.LabTechnicianTestRequestsView.as_view(), name='technician-requests'),
    path('technician/requests/<uuid:pk>/update/', views.LabTechnicianUpdateResultsView.as_view(), name='technician-update-results'),

    # Field Inspector views
    path('inspector/samples/create/', views.FieldInspectorSampleCreateView.as_view(), name='inspector-create-sample'),
    path('inspector/samples/', views.FieldInspectorSamplesView.as_view(), name='inspector-samples'),

    # Admin test types
    path('admin/types/', views.AdminTestTypeListView.as_view(), name='admin-test-types'),
    path('admin/types/<uuid:pk>/', views.AdminTestTypeDetailView.as_view(), name='admin-test-type-detail'),

    # Admin assignments
    path('admin/assignments/', views.AdminAssignmentListView.as_view(), name='admin-assignments'),
    path('admin/assignments/create/', views.AdminCreateAssignmentView.as_view(), name='admin-create-assignment'),
    path('admin/assignments/<uuid:pk>/', views.AdminRemoveAssignmentView.as_view(), name='admin-remove-assignment'),

    # Admin all requests
    path('admin/requests/', views.AdminTestRequestListView.as_view(), name='admin-test-requests'),
    path('admin/requests/<uuid:pk>/assign/', views.AdminAssignTestRequestView.as_view(), name='admin-assign-test-request'),
    path('admin/requests/<uuid:pk>/review/', views.AdminReviewTestRequestView.as_view(), name='admin-review-test-request'),

    # Officer views
    path('officer/assigned-tests/', views.OfficerAssignedTestsView.as_view(), name='officer-assigned-tests'),
    path('officer/test-requests/', views.OfficerTestRequestsView.as_view(), name='officer-test-requests'),
    path('officer/test-requests/<uuid:pk>/', views.OfficerUpdateTestStatusView.as_view(), name='officer-update-status'),
]
