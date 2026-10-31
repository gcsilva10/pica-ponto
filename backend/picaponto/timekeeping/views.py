from datetime import date, datetime, time, timedelta, timezone as datetime_timezone

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from users.models import User
from users.views import user_data

from .models import TimeEntry


def entry_data(entry):
    return {
        'id': entry.pk,
        'worker_id': entry.worker_id,
        'started_at': entry.started_at.isoformat(),
        'ended_at': entry.ended_at.isoformat() if entry.ended_at else None,
        'is_running': entry.ended_at is None,
    }


def allowed_workers(request):
    user = request.user
    if user.is_staff or user.is_superuser:
        workers = User.objects.filter(role=User.Roles.WORKER)
    elif user.is_employer():
        workers = user.workers.filter(role=User.Roles.WORKER)
    else:
        workers = User.objects.filter(pk=user.pk, role=User.Roles.WORKER)

    worker_id = request.GET.get('worker_id')
    if worker_id:
        if not worker_id.isdecimal():
            return None, JsonResponse({'error': 'Invalid worker_id.'}, status=400)
        workers = workers.filter(pk=int(worker_id))
        if not workers.exists():
            return None, JsonResponse({'error': 'Worker not found or access denied.'}, status=404)
    return workers, None


def period_window(request):
    period = request.GET.get('period', 'day')
    if period not in ('day', 'week'):
        return None, JsonResponse({'error': 'period must be day or week.'}, status=400)
    raw_date = request.GET.get('date')
    try:
        selected = date.fromisoformat(raw_date) if raw_date else timezone.localdate()
    except ValueError:
        return None, JsonResponse({'error': 'date must be YYYY-MM-DD.'}, status=400)
    first = selected - timedelta(days=selected.weekday()) if period == 'week' else selected
    days = 7 if period == 'week' else 1
    zone = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(first, time.min), zone)
    end = timezone.make_aware(datetime.combine(first + timedelta(days=days), time.min), zone)
    return (period, first, days, start, end), None


def scoped_entries(workers, start, end):
    return TimeEntry.objects.filter(worker__in=workers, started_at__lt=end).filter(
        Q(ended_at__gt=start) | Q(ended_at__isnull=True)
    ).select_related('worker').order_by('worker_id', 'started_at')


@require_POST
def start(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)
    if not request.user.is_worker():
        return JsonResponse({'error': 'Worker access required.'}, status=403)
    try:
        with transaction.atomic():
            entry = TimeEntry.objects.create(worker=request.user, started_at=timezone.now())
    except IntegrityError:
        return JsonResponse({'error': 'An entry is already running.'}, status=409)
    return JsonResponse({'entry': entry_data(entry)}, status=201)


@require_POST
def stop(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)
    if not request.user.is_worker():
        return JsonResponse({'error': 'Worker access required.'}, status=403)
    entry = TimeEntry.objects.filter(worker=request.user, ended_at__isnull=True).first()
    if entry is None:
        return JsonResponse({'error': 'No entry is running.'}, status=409)
    ended_at = timezone.now()
    updated = TimeEntry.objects.filter(pk=entry.pk, ended_at__isnull=True, started_at__lt=ended_at).update(
        ended_at=ended_at
    )
    if not updated:
        return JsonResponse({'error': 'Entry already stopped.'}, status=409)
    entry.ended_at = ended_at
    return JsonResponse({'entry': entry_data(entry)})


@require_GET
def entries(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)
    window, error = period_window(request)
    if error:
        return error
    workers, error = allowed_workers(request)
    if error:
        return error
    period, first, _, start_at, end_at = window
    items = scoped_entries(workers, start_at, end_at)
    return JsonResponse({'period': period, 'date': first.isoformat(),
                         'entries': [entry_data(entry) for entry in items]})


@require_GET
def report(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)
    window, error = period_window(request)
    if error:
        return error
    workers, error = allowed_workers(request)
    if error:
        return error
    period, first, days, start_at, end_at = window
    now = timezone.now()
    zone = timezone.get_current_timezone()
    by_worker = {worker.pk: {'worker': user_data(worker), 'total_seconds': 0, 'days': []}
                 for worker in workers.order_by('username')}
    for worker_report in by_worker.values():
        worker_report['days'] = [
            {'date': (first + timedelta(days=offset)).isoformat(), 'total_seconds': 0}
            for offset in range(days)
        ]
    for entry in scoped_entries(workers, start_at, end_at):
        worker_report = by_worker[entry.worker_id]
        effective_end = entry.ended_at or now
        for offset, day_report in enumerate(worker_report['days']):
            day = first + timedelta(days=offset)
            day_start = timezone.make_aware(datetime.combine(day, time.min), zone)
            day_end = timezone.make_aware(datetime.combine(day + timedelta(days=1), time.min), zone)
            overlap_start = max(entry.started_at, day_start).astimezone(datetime_timezone.utc)
            overlap_end = min(effective_end, day_end).astimezone(datetime_timezone.utc)
            seconds = max(0, int((overlap_end - overlap_start).total_seconds()))
            day_report['total_seconds'] += seconds
            worker_report['total_seconds'] += seconds
    return JsonResponse({'period': period, 'date': first.isoformat(),
                         'total_seconds': sum(item['total_seconds'] for item in by_worker.values()),
                         'workers': list(by_worker.values())})
