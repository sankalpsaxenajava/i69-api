from django.core.management.base import BaseCommand
from defaultPicker.models import *
from user.models import *

class Command(BaseCommand):
    def handle(self, *args, **options):

        moderators = ModeratorQue.objects.filter(isAssigned=True)
        if moderators.count() > 0:
            workers = User.objects.filter(roles__role__in=['CHATTER','REGULAR'])
            for worker in workers:
                fake_users = worker.fake_users.all()
                while(True):
                    for moderator in moderators:
                        if fake_users.count() < 5:
                            x_moderator = User.objects.filter(id=moderator.moderator_id).first()
                            if x_moderator not in worker.fake_users.all():
                                if x_moderator.owned_by.all():
                                    worker.fake_users.add(x_moderator)
                        else:
                            break
                    break


