from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

class User(AbstractUser):

    class Roles(models.TextChoices):
        EMPLOYER = 'EMPLOYER', 'employer'
        WORKER = 'WORKER', 'worker'

    role = models.CharField(max_length=10, choices=Roles.choices, default=Roles.WORKER)

    email = models.EmailField(unique=True)
    employer = models.ForeignKey('self', blank=True, null=True, on_delete=models.PROTECT,
                                 related_name='workers')


    def __str__(self):
        return f'{self.username} ({self.role})'

    def is_employer(self):
        return self.role == self.Roles.EMPLOYER

    def is_worker(self):
        return self.role == self.Roles.WORKER

    def clean(self):
        super().clean()
        if self.employer_id:
            if self.role != self.Roles.WORKER:
                raise ValidationError({'employer': 'Only workers can have an employer.'})
            if self.employer_id == self.pk or not self.employer.is_employer():
                raise ValidationError({'employer': 'Select a different user with the employer role.'})
