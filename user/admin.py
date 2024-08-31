from django.contrib import admin
from django.contrib.admin.options import ModelAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

# Register your models here.
from django.contrib.auth.forms import (
    AdminPasswordChangeForm,
    UserChangeForm, 
    UserCreationForm,
)
import os
from django.utils.html import conditional_escape
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.db import router, transaction
from django.utils.translation import gettext, gettext_lazy as _
from django.http import Http404, HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.contrib import admin, messages
from django.urls import path, reverse
from django.utils.html import escape
from django.contrib.admin.utils import unquote
from django.contrib.auth import update_session_auth_hash
from django.template.response import TemplateResponse
from django.contrib.admin.options import IS_POPUP_VAR
from chat.models import send_notification_fcm
from django.conf import settings
from chat.models import Notification
from string import Template
from django.utils.safestring import mark_safe
from django.forms import ImageField
from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import escape, conditional_escape
from django.db.models import Q

from django.forms.widgets import ClearableFileInput, Input, CheckboxInput, SelectMultiple

from worker.models import WorkerInvitation
from .models import *
from gifts.models import Gift, Giftpurchase

from easy_select2 import select2_modelform

from import_export import resources
from import_export.admin import ImportExportModelAdmin, ExportActionMixin

from purchase.models import Purchase

admin.site.register(ModeratorQue)

csrf_protect_m = method_decorator(csrf_protect)
sensitive_post_parameters_m = method_decorator(sensitive_post_parameters())

from django.contrib.admin import SimpleListFilter

class CoinPurchaseFilter(SimpleListFilter):
    title = 'Purchased coins' # or use _('country') for translated title
    parameter_name = 'purchased_coins'

    def lookups(self, request, model_admin):
        return [("Yes","Yes"),("No","No")]

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.exclude(purchase_coins_date=None)
        if self.value() == 'No':
            return queryset.filter(purchase_coins_date=None)
        return queryset

class RealUser(User):
    class Meta:
        proxy = True
        verbose_name = '_Real User'
        verbose_name_plural = '_Real Users'

@admin.register(RealUser)
class UserAdmin(ModelAdmin):

    change_user_password_template = None
    list_display = [
        "username",
        "fullName",
        "socialProvider",
        "gender",
        "is_staff",
        "is_superuser",
        "last_login",
        "date_joined",
        "coins",
        "user_images"
    ]
    list_filter=("gender",CoinPurchaseFilter,"age")
    def coins(self,obj):
        return obj.purchase_coins+obj.gift_coins
    
    def get_queryset(self, request):
        qs = super(UserAdmin, self).get_queryset(request)
        qs = qs.filter(owned_by=None,is_staff=False).exclude(roles__role__in=['CHATTER','ADMIN'])
        qs = qs.order_by('last_login').reverse()
        qs = qs.exclude(last_login=None)
        return qs
    
    def user_images(self, obj):
        pics = UserPhoto.objects.filter(user=obj)
        strcol = []
        strcol.append('<div style="width:230px"><ul class="mwrap">')
        for pic in pics:
            if pic.file:
                pic_url = pic.file.url
                strcol.append( "<li><a class='mtooltip left' href='javascript:;'><img src='"+pic_url+"' width='30px'/><span><img src='"+pic_url+"' style='max-width:300px;max-height:300px;'/></span></a></li>" )
            else:
                strcol.append(
                    "<li><a class='mtooltip left' href='javascript:;'><img src='" + pic.file_url + "' width='30px'/><span><img src='" + pic_url + "' style='max-width:300px;max-height:300px;'/></span></a></li>")
        strcol.append('</ul></div>')
        if len(strcol) > 0:
            style_css = """
            <style>
            a.mtooltip { outline: none; cursor: help; text-decoration: none; position: relative;}
            a.mtooltip span {margin-left: -999em; padding:5px 6px; position: absolute; width:auto; white-space:nowrap; line-height:1.5;box-shadow:0px 0px 10px #999; -moz-box-shadow:0px 0px 10px #999; -webkit-box-shadow:0px 0px 10px #999; border-radius:3px 3px 3px 3px; -moz-border-radius:3px; -webkit-border-radius:3px;}
            a.mtooltip span img {max-width:300px;}
            a.mtooltip {background:#ffffff; text-decoration:none;cursor: help;} /*BG color is a must for IE6*/
            a.mtooltip:hover span{ right: 1em;top: 2em; margin-left: 0; z-index:99999; position:absolute; background:#ffffff; border:1px solid #cccccc; color:#6c6c6c;}

            #changelist-form .results{overflow-x: initial!important;}
            ul.mwrap {list-style:none;}
            ul.mwrap li{margin:0; padding:3px;list-style:none;float:left;}
            ul.mwrap li:nth-child(5n+1) {clear:left;}
            </style>
            """
            strcol.append( style_css )
            #str.append( '<link rel="stylesheet" type="text/css" href="'+settings.STATIC_URL+'admin/css/tooltip.css"/>')

        return mark_safe(u''.join(strcol))

    help_texts = {"password": "bla bla"}
    # fieldsets = [
    #     (
    #         "Password", {
    #             "fields": ("password",), 
    #             "description": "bla bla"
    #             })
    # ]
    readonly_fields = ("id", "password","purchase_coins","purchase_coins_date")
    search_fields = ["id", "username", "fullName", "email"]
    exclude = ('password',)
    filter_horizontal = ("blockedUsers",)
    change_password_form = AdminPasswordChangeForm
    order_by = ['user_name',"coins",]

    def save_model(self, request, obj, form, change):
        if form.is_valid():
            if ('purchase_coins' in form.changed_data) or ('gift_coins' in form.changed_data):
                username=form.cleaned_data['username']
                user = User.objects.filter(username=username).last()
                sender = request.user

                if "purchase_coins" in form.changed_data:
                    coins = form.cleaned_data['purchase_coins']
                    changed_coins=int(coins)-int(user.purchase_coins)
                    notification_obj=Notification(sender=sender, user=user, notification_setting_id="ADMIN")
                    data = {'coins': str(coins)}
                    notification_obj.data=data
                    try:
                        send_notification_fcm(notification_obj, coins=changed_coins,current_coins=coins)
                    except Exception as e:
                        raise Exception(str(e))
                if('gift_coins' in form.changed_data):
                    coins = form.cleaned_data['gift_coins']
                    changed_coins=int(coins)-int(user.gift_coins)

                    notification_obj=Notification(sender=sender, user=user, notification_setting_id="ADMIN")
                    data = {'coins': str(coins)}
                    notification_obj.data=data
                    try:
                        send_notification_fcm(notification_obj, coins=changed_coins,current_coins=coins)
                    except Exception as e:
                        raise Exception(str(e))
        super().save_model(request, obj, form, change)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults["form"] = self.add_form
        defaults.update(kwargs)
        # add password hint text
        defaults.update({'help_texts': {'password': 'To change password use <a href="../password">this form</a>'}})
        return super().get_form(request, obj, **defaults)

    def get_urls(self):
        return [
            path(
                "<id>/password/",
                self.admin_site.admin_view(self.user_change_password),
                name="auth_user_password_change",
            ),
        ] + super().get_urls()

    def lookup_allowed(self, lookup, value):
        # Don't allow lookups involving passwords.
        return not lookup.startswith("password") and super().lookup_allowed(
            lookup, value
        )

    @sensitive_post_parameters_m
    @csrf_protect_m
    def add_view(self, request, form_url="", extra_context=None):
        with transaction.atomic(using=router.db_for_write(self.model)):
            return self._add_view(request, form_url, extra_context)

    def _add_view(self, request, form_url="", extra_context=None):
        # It's an error for a user to have add permission but NOT change
        # permission for users. If we allowed such users to add users, they
        # could create superusers, which would mean they would essentially have
        # the permission to change users. To avoid the problem entirely, we
        # disallow users from adding users if they don't have change
        # permission.
        if not self.has_change_permission(request):
            if self.has_add_permission(request) and settings.DEBUG:
                # Raise Http404 in debug mode so that the user gets a helpful
                # error message.
                raise Http404(
                    'Your user does not have the "Change user" permission. In '
                    "order to add users, Django requires that your user "
                    'account have both the "Add user" and "Change user" '
                    "permissions set."
                )
            raise PermissionDenied
        if extra_context is None:
            extra_context = {}
        username_field = self.model._meta.get_field(self.model.USERNAME_FIELD)
        defaults = {
            "auto_populated_fields": (),
            "username_help_text": username_field.help_text,
        }
        extra_context.update(defaults)
        return super().add_view(request, form_url, extra_context)

    @sensitive_post_parameters_m
    def user_change_password(self, request, id, form_url=""):
        user = self.get_object(request, unquote(id))
        if not self.has_change_permission(request, user):
            raise PermissionDenied
        if user is None:
            raise Http404(
                _("%(name)s object with primary key %(key)r does not exist.")
                % {
                    "name": self.model._meta.verbose_name,
                    "key": escape(id),
                }
            )
        if request.method == "POST":
            form = self.change_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                change_message = self.construct_change_message(request, form, None)
                self.log_change(request, user, change_message)
                msg = gettext("Password changed successfully.")
                messages.success(request, msg)
                update_session_auth_hash(request, form.user)
                return HttpResponseRedirect(
                    reverse(
                        "%s:%s_%s_change"
                        % (
                            self.admin_site.name,
                            user._meta.app_label,
                            user._meta.model_name,
                        ),
                        args=(user.pk,),
                    )
                )
        else:
            form = self.change_password_form(user)

        fieldsets = [(None, {"fields": list(form.base_fields)})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            "title": _("Change password: %s") % escape(user.get_username()),
            "adminForm": adminForm,
            "form_url": form_url,
            "form": form,
            "is_popup": (IS_POPUP_VAR in request.POST or IS_POPUP_VAR in request.GET),
            "add": True,
            "change": False,
            "has_delete_permission": False,
            "has_change_permission": True,
            "has_absolute_url": False,
            "opts": self.model._meta,
            "original": user,
            "save_as": False,
            "show_save": True,
            **self.admin_site.each_context(request),
        }

        request.current_app = self.admin_site.name

        return TemplateResponse(
            request,
            self.change_user_password_template
            or "admin/auth/user/change_password.html",
            context,
        )
class UserStaff(User):
    class Meta:
        proxy = True
        verbose_name = '_User Admin'
        verbose_name_plural = '_User Admins'

@admin.register(UserStaff)
class UserStaffAdmin(UserAdmin):
    def get_queryset(self, request):
        qs = User.objects.filter(roles__role__in=['ADMIN'])
        return qs

class UserModerator(User):
    class Meta:
        proxy = True
        verbose_name = '_User Moderator'
        verbose_name_plural = '_User Moderators'

@admin.register(UserModerator)
class UserModeratorAdmin(UserAdmin):
    def get_queryset(self, request):
        qs = User.objects.filter(roles__role__in=['MODERATOR'])
        return qs

class UserWorker(User):
    class Meta:
        proxy = True
        verbose_name = '_Worker'
        verbose_name_plural = '_Workers'

@admin.register(UserWorker)
class UserWorkerAdmin(UserAdmin):
    def get_queryset(self, request):
        qs = User.objects.filter(roles__role__in=['CHATTER'])
        return qs

@admin.register(UserSocialProfile)
class UserSocialProfileAdmin(
    ImportExportModelAdmin, ExportActionMixin, admin.ModelAdmin
):
    pass


@admin.register(CoinSettings)
class CoinSettingsAdmin(ImportExportModelAdmin, ExportActionMixin, admin.ModelAdmin):
    pass


admin.site.register(UserRole)
admin.site.register(WorkerInvitation)

# admin.site.register(UserPhoto)

class AdminImageWidget(ClearableFileInput):


    def render(self, name, value, attrs=None, renderer=None):
        output = []
        if value and getattr(value, 'url', None):
            image_url = value.url
            file_name = str(value)
            output.append(
                
                u'<a href="%s" target="_blank">'
                u'<img src="%s" alt="%s" style="max-width: 200px; max-height: 200px; border-radius: 5px;" />'
                u'</a><br/><br/> '
                % ( image_url, image_url, file_name)
            )
        output.append(super(ClearableFileInput, self).render(name, value, attrs))
        return mark_safe(u''.join(output))


class UserPhotoAdminForm(forms.ModelForm):
    class Meta:
        model = UserPhoto
        fields = '__all__'
        widgets = {
            'file': AdminImageWidget
        }
    
    
    
@admin.register(UserPhoto)
class UserPhotoAdmin(ModelAdmin):
    list_display = ('id', 'user', 'view_thumbnail')
    search_fields = ["user__username", "user__fullName", "user__email"]
    form = UserPhotoAdminForm

    def view_thumbnail(self, obj):
        output = []
        if obj.file:
            image_url = obj.file.url
            output.append(
                u'<a href="javascript:;" class="mtooltip left">'
                u'<img src="%s" alt="" style="max-width: 30px; max-height: 30px;" />'
                u'<span><img src="%s" style="max-width: 300px; max-height: 300px;"/></span>'
                u'</a>'
                % ( image_url, image_url)
            )

            style_css = """
            <style>
            a.mtooltip { outline: none; cursor: help; text-decoration: none; position: relative;}
            a.mtooltip span {margin-left: -999em; padding:5px 6px; position: absolute; width:auto; white-space:nowrap; line-height:1.5;box-shadow:0px 0px 10px #999; -moz-box-shadow:0px 0px 10px #999; -webkit-box-shadow:0px 0px 10px #999; border-radius:3px 3px 3px 3px; -moz-border-radius:3px; -webkit-border-radius:3px;}
            a.mtooltip span img {max-width:300px;}
            a.mtooltip {background:#ffffff; text-decoration:none;cursor: help;} /*BG color is a must for IE6*/
            a.mtooltip:hover span{ left: 1em;top: 0em; margin-left: 0; z-index:99999; position:absolute; background:#ffffff; border:1px solid #cccccc; color:#6c6c6c;}

            #changelist-form .results{overflow-x: initial!important;}
            </style>
            """
            output.append( style_css )
        if obj.file_url:
            image_url = obj.file_url
            output.append(
                u'<a href="javascript:;" class="mtooltip left">'
                u'<img src="%s" alt="" style="max-width: 30px; max-height: 30px;" />'
                u'<span><img src="%s" style="max-width: 300px; max-height: 300px;"/></span>'
                u'</a>'
                % (image_url, image_url)
            )

            style_css = """
                        <style>
                        a.mtooltip { outline: none; cursor: help; text-decoration: none; position: relative;}
                        a.mtooltip span {margin-left: -999em; padding:5px 6px; position: absolute; width:auto; white-space:nowrap; line-height:1.5;box-shadow:0px 0px 10px #999; -moz-box-shadow:0px 0px 10px #999; -webkit-box-shadow:0px 0px 10px #999; border-radius:3px 3px 3px 3px; -moz-border-radius:3px; -webkit-border-radius:3px;}
                        a.mtooltip span img {max-width:300px;}
                        a.mtooltip {background:#ffffff; text-decoration:none;cursor: help;} /*BG color is a must for IE6*/
                        a.mtooltip:hover span{ left: 1em;top: 0em; margin-left: 0; z-index:99999; position:absolute; background:#ffffff; border:1px solid #cccccc; color:#6c6c6c;}

                        #changelist-form .results{overflow-x: initial!important;}
                        </style>
                        """
            output.append(style_css)
        return mark_safe(u''.join(output))
        
# @admin.register(CoinsHistory)
# class CoinsHistoryAdmin(admin.ModelAdmin):
#     list_display=['user','coins_purchased','coins_gifted']
#     ordering = ('user',) #'coins_purchased','coins_gifted')
#     search_fields = ["user__username", "user__fullName", "user__email"]

#     #must show current values of the user table;
#     def coins_purchased(self, obj):
#         return User.objects.values('purchase_coins').filter(id=obj.user.id).first()['purchase_coins']

#     def coins_gifted(self, obj):
#         return User.objects.values('gift_coins').filter(id=obj.user.id).first()['gift_coins']
        
#     readonly_fields=[
#         'user','purchase_coins','gift_coins','actor'
#     ]
#     def get_queryset(self, request):
#         return CoinsHistory.objects.all().order_by("user").distinct("user")
#     def get_purchase_history_list(self, user_id):
#         return CoinsHistory.objects.filter(user_id=user_id).filter(purchase_coins__gte=1).order_by('-date_created')
#     def get_gift_history_list(self, user_id):
#         return Giftpurchase.objects.filter(receiver=user_id).order_by('-purchased_on')

#     def change_view(self, request, object_id, extra_context=None):
#         extra_context = extra_context or {}
#         temp=CoinsHistory.objects.get(id=object_id)
#         user=temp.user
#         extra_context['purchase_history_list'] = self.get_purchase_history_list(user_id=user.id)
#         extra_context['gift_history_list'] = self.get_gift_history_list(user_id=user.id)
#         #print(extra_context['purchase_history_list'])
#         #print(extra_context['gift_history_list'])
#         return super(CoinsHistoryAdmin, self).history_view(
#             request, object_id, extra_context=extra_context,
#         )

#     def has_add_permission(self, request, obj=None):
#         return False

# CoinHistorys is a proxy model for User.
@admin.register(CoinsHistorys)
class CoinsHistorysAdmin(admin.ModelAdmin):
    list_display=['username','gift_coins','gift_coins_date', 'purchase_coins','purchase_coins_date']
    ordering = ('username',)
    order_by = ('username','gift_coins','gift_coins_date', 'purchase_coins','purchase_coins_date')
    search_fields = ["username", "fullName", "email"]
    # readonly_fields=[
    #     'user','purchase_coins','gift_coins','actor'
    # ]
    def get_queryset(self, request):
        return User.objects.filter(Q(purchase_coins__gte=1) | Q(gift_coins__gte=1)).order_by("username")
    def get_purchase_history_list(self, user_id):
        return CoinsHistory.objects.filter(user_id=user_id).filter(purchase_coins__gte=1).order_by('-date_created')
    def get_gift_history_list(self, user_id):
        return Giftpurchase.objects.filter(receiver=user_id).order_by('-purchased_on')

    def change_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        #print(object_id)
        #temp=CoinsHistory.objects.get(id=object_id)
        #user=temp.user
        user = User.objects.get(pk=object_id)
        extra_context['purchase_history_list'] = self.get_purchase_history_list(user_id=user.id)
        extra_context['gift_history_list'] = self.get_gift_history_list(user_id=user.id)
        #print(extra_context['purchase_history_list'])
        #print(extra_context['gift_history_list'])
        return super(CoinsHistorysAdmin, self).history_view(
            request, object_id, extra_context=extra_context,
        )

    def has_add_permission(self, request, obj=None):
        return False
    