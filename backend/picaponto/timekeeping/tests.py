import json
from datetime import datetime, timezone

from django.test import Client, TestCase
from django.urls import reverse

from users.models import User

from .models import TimeEntry


class TimekeepingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.employer = User.objects.create_user(username='boss', email='boss@example.com',
                                                password='pass12345', role=User.Roles.EMPLOYER)
        cls.other_employer = User.objects.create_user(username='other', email='other@example.com',
                                                      password='pass12345', role=User.Roles.EMPLOYER)
        cls.worker = User.objects.create_user(username='worker', email='worker@example.com',
                                              password='pass12345', employer=cls.employer)
        cls.other_worker = User.objects.create_user(username='other-worker', email='other-worker@example.com',
                                                    password='pass12345', employer=cls.other_employer)
        cls.admin = User.objects.create_superuser(username='admin', email='admin@example.com',
                                                  password='pass12345', role=User.Roles.EMPLOYER)

    def test_login_and_csrf_protection(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('login'), data=json.dumps({
            'username': 'worker', 'password': 'pass12345',
        }), content_type='application/json').status_code, 403)
        client.get(reverse('csrf'))
        token = client.cookies['csrftoken'].value
        response = client.post(reverse('login'), data=json.dumps({
            'username': 'worker', 'password': 'pass12345',
        }), content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.get(reverse('me')).json()['user']['role'], User.Roles.WORKER)

    def test_worker_can_start_and_stop_multiple_entries(self):
        self.client.force_login(self.worker)
        first = self.client.post(reverse('entry_start'))
        self.assertEqual(first.status_code, 201)
        self.assertEqual(self.client.post(reverse('entry_start')).status_code, 409)
        self.assertEqual(self.client.post(reverse('entry_stop')).status_code, 200)
        self.assertEqual(self.client.post(reverse('entry_stop')).status_code, 409)
        self.assertEqual(self.client.post(reverse('entry_start')).status_code, 201)
        self.assertEqual(TimeEntry.objects.filter(worker=self.worker).count(), 2)

    def test_employer_can_only_see_own_workers(self):
        TimeEntry.objects.create(worker=self.worker, started_at=datetime(2026, 10, 30, 9, tzinfo=timezone.utc),
                                 ended_at=datetime(2026, 10, 30, 10, tzinfo=timezone.utc))
        TimeEntry.objects.create(worker=self.other_worker, started_at=datetime(2026, 10, 30, 9, tzinfo=timezone.utc),
                                 ended_at=datetime(2026, 10, 30, 10, tzinfo=timezone.utc))
        self.client.force_login(self.employer)
        url = reverse('report') + '?date=2026-10-30'
        report = self.client.get(url).json()
        self.assertEqual([item['worker']['id'] for item in report['workers']], [self.worker.pk])
        self.assertEqual(self.client.get(url + f'&worker_id={self.other_worker.pk}').status_code, 404)
        self.assertEqual(self.client.post(reverse('entry_start')).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(len(self.client.get(url).json()['workers']), 2)

    def test_weekly_report_splits_entries_at_local_midnight(self):
        # In Lisbon on 30 October, these UTC times cross local midnight.
        TimeEntry.objects.create(worker=self.worker,
                                 started_at=datetime(2026, 10, 30, 23, 30, tzinfo=timezone.utc),
                                 ended_at=datetime(2026, 10, 31, 0, 30, tzinfo=timezone.utc))
        self.client.force_login(self.worker)
        report = self.client.get(reverse('report') + '?period=week&date=2026-10-31').json()
        self.assertEqual(report['date'], '2026-10-26')
        self.assertEqual(report['total_seconds'], 3600)
        days = report['workers'][0]['days']
        self.assertEqual(days[4]['total_seconds'], 1800)
        self.assertEqual(days[5]['total_seconds'], 1800)
        self.assertEqual(len(self.client.get(reverse('entries') + '?period=week&date=2026-10-31').json()['entries']), 1)

    def test_report_counts_real_seconds_across_daylight_saving_change(self):
        TimeEntry.objects.create(worker=self.worker,
                                 started_at=datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc),
                                 ended_at=datetime(2026, 10, 25, 2, 30, tzinfo=timezone.utc))
        self.client.force_login(self.worker)
        report = self.client.get(reverse('report') + '?date=2026-10-25').json()
        self.assertEqual(report['total_seconds'], 7200)
