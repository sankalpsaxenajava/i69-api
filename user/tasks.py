from celery import shared_task
from django.utils import timezone
from chat.models import Message, Room,Notification, send_notification_fcm
from django.db.models import Q, Count
from user.models import ModeratorQue, User
from django.utils import timezone

@shared_task(name = "unassign_moderator_from_inactive_workers")
def unassign_moderator_from_inactive_workers(*args, **kwargs):
    time_before_6_minutes=timezone.now() - timezone.timedelta(minutes=6)
    print(f" time befor 6 minutes {time_before_6_minutes}")
    messages=Message.objects.filter(timestamp__gt=time_before_6_minutes,read=None,user_id__roles__role__in=['REGULAR']).filter(Q(room_id__user_id__roles__role__in=["MODERATOR"])|Q(room_id__target__roles__role__in=["MODERATOR"]))

    rooms_id_list=set(messages.values_list("room_id",flat=True))

    rooms=Room.objects.filter(id__in=rooms_id_list)

    users=[]
    for room in rooms:
        if room.user_id.roles.filter(role__in=['MODERATOR']):
            users.append(room.user_id)
        else:
            users.append(room.target)
    available_workers=User.objects.filter(roles__role__in=['CHATTER']).annotate(fake_count=Count("fake_users")).filter(fake_count__lt=5)
    
    workers_with_5_moderators=[]
    print(f"Moderators {users}")
    while len(users):
        if list(available_workers)==workers_with_5_moderators:
            print("All workers are busy")
            break
        for worker in available_workers:
            if worker in workers_with_5_moderators:
                continue
            if worker.fake_users.all().count()<5:
                print(f"User {users[-1]}")
                old_worker=users[-1].owned_by.all()[0]
                if old_worker==worker:
                    continue

                moderator=users.pop()
                moderator.owned_by.remove(old_worker)
                moderator.owned_by.add(worker)
                print(f"moderator {moderator} removed from {old_worker} added to {worker}")

            else:
                print("{worker} worker is  busy")

                workers_with_5_moderators.append(worker)

            if len(users)==0:
                break

    if users:
        for user in users:
            ModeratorQue.objects.get_or_create(moderator=user)
        print(f"{users} are the users added to uqueue.")



    print(f"the users(moderators) who's owners has not taken action from last 6 minuts are {users}")


@shared_task(name="assign_moderator_from_inactive_to_active_workers")
def assign_moderator_from_inactive_to_active_workers(*args, **kwargs):
    workers = User.objects.filter(roles__role__in=['CHATTER'])
    for worker in workers:
        user_token=None
        try:
            user_token=worker.auth_token
        except:
            print("No auth token")
        
        if user_token:
            now = timezone.now()
            print("-------------",user_token.created)
            print("Worker last seen was :", now - user_token.created)
            if now > user_token.created + timezone.timedelta(
                    seconds=1800):
                # logout the worker
                try:
                    worker.auth_token.delete()
                    print("Logging out worker.")
                except:
                    print("Token already deleted.")

                current_moderators = worker.fake_users.all()
                if current_moderators.count() > 0:
                    for moderator in current_moderators:
                        old_owner = moderator.owned_by.all()[0]
                        moderator.owned_by.remove(old_owner)
                        push_moderator = ModeratorQue.objects.create(moderator=moderator)
                        print("Moderator added in que : ")
                        push_moderator.save()

        print("All moderators from inactive workers moved to que successfully.")

    moderators = ModeratorQue.objects.filter(isAssigned=False)
    if moderators.count() > 0:
        print("Assigning moderators to active workers : ")
        for worker in workers:
            print("checking for worker : ",worker.fullName)
            while (True):
                for moderator in moderators:
                    if worker.fake_users.count() < 5 and worker.isOnline:
                        x_moderator = User.objects.filter(id=moderator.moderator_id).first()
                        if x_moderator not in worker.fake_users.all():
                            if x_moderator.owned_by.all():
                                OLD=x_moderator.owned_by.all()[0]
                                x_moderator.owned_by.remove(OLD)
                                print(f"Assigned moderator {x_moderator.fullName} to worker {worker.fullName}")
                            else:
                                worker.fake_users.add(x_moderator)
                                moderator.delete()
                                print("RECORD DELETED FROM QUE....")
                    else:
                        print(f"Moderator left in que {ModeratorQue.objects.filter(isAssigned=False).count()}")
                        break
                break
        print(f"{ModeratorQue.objects.filter(isAssigned=False).count()} Moderators left in que.")


@shared_task(name = "reminder_for_unread_messages")
def reminder_for_unread_messages(*args, **kwargs):
    notification_setting = "MSGREMINDER"
    timedelta_10_min=timezone.now() - timezone.timedelta(minutes=10)
    messages=Message.objects.select_related("room_id").filter(read=None)
    notifications = Notification.objects.select_related("user").filter(created_date__gt=timedelta_10_min,notification_setting__id=notification_setting).values_list("user",flat=True)
    user_already_notified=[]
    for message in messages:
        room = message.room_id
        if room.user_id==message.user_id:
            if room.target.id in notifications:
                continue
            if room.target in user_already_notified:
                continue
    
            notification_receiver=room.target
            user_already_notified.append(room.target)
            pass
        else:
            if room.target.id in notifications:
                continue
            if room.user_id in user_already_notified:
                continue
            # TODO send notification to room.user_id
            notification_receiver=room.user_id

            user_already_notified.append(room.user_id)
            pass


        notification_obj = Notification(user=notification_receiver, notification_setting_id=notification_setting)
        send_notification_fcm(notification_obj=notification_obj)