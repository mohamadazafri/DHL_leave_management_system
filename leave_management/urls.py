from django.urls import path
from .views import (
    LeaveFormView, DashboardView, DashboardV2View,UpdateLeaveStatusView,
    LeaveListView, LeaveDetailView, BulkLeaveUploadView, BulkUploadView,
    LeaveApplicationsView, login_view, HomeView, ProcessDuplicatesView,
    DuplicateReviewView
)
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('leave/new/', LeaveFormView.as_view(), name='leave_form'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/v2/', DashboardV2View.as_view(), name='dashboard_v2'),
    path('leave/<str:leave_id>/update-status/', UpdateLeaveStatusView.as_view(), name='update_leave_status'),
    
    # API endpoints for UiPath
    path('api/leaves/', LeaveListView.as_view(), name='api_leave_list'),
    path('api/leaves/<str:pk>/', LeaveDetailView.as_view(), name='api_leave_detail'),
    path('api/leaves/bulk-upload/', BulkLeaveUploadView.as_view(), name='api_bulk_upload'),
    path('bulk-upload/', BulkUploadView.as_view(), name='bulk_upload'),
    path('leave-applications/', LeaveApplicationsView.as_view(), name='leave_applications'),
    path('login/', login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('api/leaves/process-duplicates/', ProcessDuplicatesView.as_view(), name='process-duplicates'),
    path('duplicates/review/', DuplicateReviewView.as_view(), name='duplicate_review'),
]
