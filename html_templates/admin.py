from django.contrib import admin

from html_templates.models import HTMLTemplate


class HTMLTemplateAdmin(admin.ModelAdmin):

    list_display = ['name', 'document_type']
    list_per_page = 50
    search_fields = ['name', 'html_template', 'html_context']

admin.site.register(HTMLTemplate, HTMLTemplateAdmin)
