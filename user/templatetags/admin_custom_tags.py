from django import template
from django.utils import timezone
from django.contrib.admin.models import LogEntry
register= template.Library()

@register.filter
def last_24h_logs(logs_list):
    time_delta_24h=timezone.now()-timezone.timedelta(hours=24)
    print(time_delta_24h)
    # print(logs_list.filter(action_time__gt=time_delta_24h))
    # for log in logs_list:
    #     print(log.action_time)
    return LogEntry.objects.filter(action_time__gt=time_delta_24h)