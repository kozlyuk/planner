from django.contrib import admin

from .models import News, Event


class NewsAdmin(admin.ModelAdmin):

    list_display = ['creator', 'created', 'title',
                    'news_type', 'actual_from', 'actual_to']
    ordering = ['created']
    list_filter = ['creator']
    fieldsets = [
        (None, {'fields': [('title', 'news_type'),
                           ('text',),
                           ('actual_from', 'actual_to')
                           ]})
    ]


class EventAdmin(admin.ModelAdmin):

    list_display = ['creator', 'date', 'title', 'repeat']
    ordering = ['created']
    list_filter = ['creator']
    fieldsets = [
        (None, {'fields': [('title',),
                           ('date', 'repeat'),
                           ('description',),
                           ]})
    ]


admin.site.register(News, NewsAdmin)
admin.site.register(Event, EventAdmin)
