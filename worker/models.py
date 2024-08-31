from django.db import models


class WorkerInvitation(models.Model):
    email = models.EmailField()
    token = models.UUIDField()
    is_admin_permission = models.BooleanField()
    is_chat_admin_permission = models.BooleanField()

    def __str__(self):
        return self.email
