from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class TimeEntry(models.Model):
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                               related_name='time_entries')
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-started_at']
        constraints = [
            models.UniqueConstraint(fields=['worker'], condition=Q(ended_at__isnull=True),
                                    name='one_open_entry_per_worker'),
            models.CheckConstraint(condition=Q(ended_at__isnull=True) | Q(ended_at__gt=F('started_at')),
                                   name='end_after_start'),
        ]

    def clean(self):
        if self.worker_id and not self.worker.is_worker():
            raise ValidationError({'worker': 'Time entries require a worker.'})
        if self.ended_at and self.ended_at <= self.started_at:
            raise ValidationError({'ended_at': 'End must be after start.'})

    def __str__(self):
        return f'{self.worker} — {self.started_at:%Y-%m-%d %H:%M}'
