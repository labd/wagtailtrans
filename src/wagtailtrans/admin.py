from django.conf import settings
from django.contrib import admin

from wagtailtrans import models


class LanguageAdmin(admin.ModelAdmin):
    list_display = ('code', 'position', 'is_default')


class TranslatablePageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'language')
    list_filter = ('language',)


class TranslatablePageItemAdmin(admin.ModelAdmin):
    list_display = ('page', 'canonical_page', 'language')
    list_filter = ('language',)


admin.site.register(models.Language, LanguageAdmin)
admin.site.register(models.TranslatablePage, TranslatablePageAdmin)
admin.site.register(models.TranslatablePageItem, TranslatablePageItemAdmin)
