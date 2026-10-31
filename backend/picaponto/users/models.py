from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    class Roles(models.TextChoices):
        EMPLOYER = 'EMPLOYER', 'employer'
        WORKER = 'WORKER', 'worker'

    role = models.CharField(max_length=10, choices=Roles.choices, default=Roles.WORKER)

    email = models.EmailField(unique=True)


    def __str__(self):
        return f'{self.username} ({self.role})'

    def is_employer(self):
        return self.role == self.Roles.EMPLOYER

    def is_worker(self):
        return self.role == self.Roles.WORKER
    