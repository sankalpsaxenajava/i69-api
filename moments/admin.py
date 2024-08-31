from django.contrib import admin
from django.contrib.admin.options import ModelAdmin
from .models import Moment,Comment,Like,Report,Story, GenericLike,GenericComment, StoryVisibleTime
from django.utils.safestring import mark_safe
from django import forms
# Register your models here.


@admin.register(Moment)
class MomentAdmin(admin.ModelAdmin):
    list_display=['user', 'Title','created_date','view_thumbnail']
    ordering = ('Title',)
    order_by = ['user', 'Title','created_date']
    search_fields = ('Title',"user__username", "user__fullName", "user__email")

    def view_thumbnail(self, obj):
        output = []
        if obj.file.url:
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
            a.mtooltip:hover span{ right: 1em;top: 0em; margin-left: 0; z-index:99999; position:absolute; background:#ffffff; border:1px solid #cccccc; color:#6c6c6c;}

            #changelist-form .results{overflow-x: initial!important;}
            </style>
            """
            output.append( style_css )

        return mark_safe(u''.join(output))

@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display=['user','created_date', 'view_thumbnail']
    ordering = ('user',)
    order_by = ['user', 'created_date']
    search_fields = ["user__username", "user__fullName", "user__email"]

    def view_thumbnail(self, obj):
        output = []
        if obj.file.url:
            video_url = obj.file.url
            if obj.thumbnail and obj.thumbnail.url:
                image_url = obj.thumbnail.url
                output.append(
                    u'<a href="javascript:;" class="mtooltip left">'
                    u'<img src="%s" alt="" style="max-width: 30px; max-height: 30px;" />'
                    u'<span><video width="320" height="240" controls>'
                    u'<source src="%s">Your browser does not support the video tag.</video>'
                    u'</span>'
                    u'</a>'
                    % ( image_url, video_url)
                )
            
            else:
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

        return mark_safe(u''.join(output))

#admin.site.register(Moment)
#admin.site.register(Story)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(Report)
admin.site.register(GenericLike)
admin.site.register(GenericComment)

class StoryVisibleAdminForm(forms.ModelForm):
    class Meta:
        model = StoryVisibleTime
        fields = ('weeks', 'days', 'hours',)




@admin.register(StoryVisibleTime)
class StoryVisibleAdmin(ModelAdmin):
    list_display = [
        "text",
        "weeks",
        "days",
        "hours"
    ]
    

    form = StoryVisibleAdminForm
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

