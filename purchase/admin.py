from django.contrib import admin
from django.contrib.admin.options import ModelAdmin

# Register your models here.

from .models import *

from easy_select2 import select2_modelform

from import_export import resources
from import_export.admin import ImportExportModelAdmin, ExportActionMixin


@admin.register(Purchase)
class PurchaseAdmin(ModelAdmin):
    list_display = ['user', 'purchased_on', 'coins', 'method', 'money']
    search_fields = ["user__username", "user__fullName", "user__email"]