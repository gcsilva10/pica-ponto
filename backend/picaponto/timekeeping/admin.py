from django.contrib import admin

from .models import TimeEntry


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ('worker', 'started_at', 'ended_at', 'employer')
    list_filter = ('worker__employer', 'worker', 'started_at', 'ended_at')
    search_fields = ('worker__username', 'worker__email', 'worker__employer__username')
    date_hierarchy = 'started_at'

    @admin.display(description='Employer')
    def employer(self, obj):
        return obj.worker.employer

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('worker__employer')
