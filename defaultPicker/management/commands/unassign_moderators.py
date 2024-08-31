from django.core.management.base import BaseCommand

from chat.models import Message
from defaultPicker.models import *
from user.models import *
from datetime import datetime, timedelta

class Command(BaseCommand):
    def handle(self, *args, **options):
        user = User.objects.filter()

        # messages = Message.objects.filter(user=user, room=room)
        messages = Message.objects.filter(user_id_id=user.id, room_id_id="26")
        if messages.count() > 0:
            coins = CoinSettings.objects.filter(method='Message').first()
            if coins and coins.coins_needed > 0:
                user.deductCoins(coins.coins_needed)
        # for worker in workers:
        #     try:
        #         print(worker.avatar().file.url)
        #     except:
        #         print("url is null")


        #     print(worker.last_seen())
        #     if worker.last_seen():
        #         now = datetime.now()
        #         print("Worker last seen was :", now - worker.last_seen())
        #         if now > worker.last_seen() + timedelta(
        #                 seconds=600):
        #             # logout the worker
        #             try:
        #                 worker.auth_token.delete()
        #                 print("Logging out worker.")
        #             except:
        #                 print("Token already deleted.")
        #
        #             current_moderators = worker.fake_users.all()
        #             if current_moderators.count() > 0:
        #                 for moderator in current_moderators:
        #                     old_owner = moderator.owned_by.all()[0]
        #                     moderator.owned_by.remove(old_owner)
        #                     push_moderator = ModeratorQue.objects.create(moderator=moderator)
        #                     print("Moderator added in que : ")
        #                     push_moderator.save()
        #
        # moderators = ModeratorQue.objects.filter(isAssigned=False)
        # if moderators.count() > 0:
        #     print("Assigning moderators to active workers : ")
        #     for worker in workers:
        #         print("checking for worker : ", worker.fullName)
        #         while (True):
        #             for moderator in moderators:
        #                 if worker.fake_users.count() < 5 & worker.isOnline:
        #                     x_moderator = User.objects.filter(id=moderator.moderator_id).first()
        #                     if x_moderator not in worker.fake_users.all():
        #                         if x_moderator.owned_by.all():
        #                             print(f"Assigned moderator {x_moderator.fullName} to worker {worker.fullName}")
        #                             worker.fake_users.add(x_moderator)
        #                             moderator.delete()
        #                             print("RECORD DELETED FROM QUE....")
        #                 else:
        #                     print(f"Moderator left in que {ModeratorQue.objects.filter(isAssigned=False).count()}")
        #                     break
        #             break
        #
