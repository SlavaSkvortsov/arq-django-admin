from django.urls import path

from arq_admin.views import (
    AllJobListView, CompleteJobListView, DeferredJobListView, JobDetailView,
    QueuedJobListView, QueueListView, RunningJobListView,
)

app_name = 'arq_admin'
urlpatterns = [
    path('', QueueListView.as_view(), name='home'),
    path('queue/<str:queue_name>/', AllJobListView.as_view(), name='all_jobs'),
    path('queue/<str:queue_name>/queued/', QueuedJobListView.as_view(), name='queued_jobs'),
    path('queue/<str:queue_name>/complete/', CompleteJobListView.as_view(), name='complete_jobs'),
    path('queue/<str:queue_name>/running/', RunningJobListView.as_view(), name='running_jobs'),
    path('queue/<str:queue_name>/deferred/', DeferredJobListView.as_view(), name='deferred_jobs'),
    path('queue/<str:queue_name>/<str:job_id>/', JobDetailView.as_view(), name='job_detail'),
]
