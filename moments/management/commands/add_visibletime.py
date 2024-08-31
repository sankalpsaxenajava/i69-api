from django.core.management.base import BaseCommand, CommandError
from moments.models import StoryVisibleTime
import datetime


class Command(BaseCommand):
    help = f"adds an object for model StoryDeletionTime"
    def handle(self, *args, **kwargs):
        if StoryVisibleTime.objects.all().count() == 0:
            StoryVisibleTime().save()