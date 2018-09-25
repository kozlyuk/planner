from django.db.models import FileField
from django.forms import forms
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _
from django.forms.widgets import FileInput
from django.utils.html import format_html
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe


class ContentTypeRestrictedFileField(FileField):
    """
    Same as FileField, but you can specify:
    * content_types - list containing allowed content_types. Example: ['application/pdf', 'image/jpeg']
    * max_upload_size - a number indicating the maximum file size allowed for upload.
            2.5MB - 2621440
            5MB - 5242880
            10MB - 10485760
            20MB - 20971520
            50MB - 52428800
            100MB 104857600
            250MB - 214958080
            500MB - 429916160
    Source: http://stackoverflow.com/questions/2472422/django-file-upload-size-limit

    """

    def __init__(self, *args, **kwargs):
        try:
            self.content_types = kwargs.pop("content_types")
        except KeyError:
            self.content_types = None

        try:
            self.file_extensions = kwargs.pop("file_extensions")
        except KeyError:
            self.file_extensions = None

        try:
            self.max_upload_size = kwargs.pop("max_upload_size")
        except KeyError:
            self.max_upload_size = None

        super(ContentTypeRestrictedFileField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        data = super(ContentTypeRestrictedFileField, self).clean(*args, **kwargs)

        file = data.file
        try:
            # Check file extension if required
            if self.file_extensions:
                found = False
                for file_extension in self.file_extensions:
                    if file.name.endswith(".%s" % file_extension):
                        found = True
                        break

                if not found:
                    raise forms.ValidationError(_('Розширення фойлу не підтримується.'))

            # Check content-type if required
            if self.content_types and file.content_type not in self.content_types:
                raise forms.ValidationError(_('Файл має бути у PDF або XLSX або DOCX форматі.'))

            # Check file size if required
            if self.max_upload_size and file._size > self.max_upload_size:
                raise forms.ValidationError(_('Файл не може бути більшим %s. Розмір підвантажуваного файлу %s') % (
                filesizeformat(self.max_upload_size), filesizeformat(file._size)))
        except AttributeError:
            pass

        return data


class NotClearableFileInput(FileInput):
    initial_text = _('Currently')
    input_text = _('Change')

    template_with_initial = '%(initial_text)s: %(initial)s <br />%(input_text)s: %(input)s'

    url_markup_template = '<a href="{0}">{1}</a>'

    def render(self, name, value, attrs=None):
        substitutions = {
            'initial_text': self.initial_text,
            'input_text': self.input_text,
        }
        template = '%(input)s'
        substitutions['input'] = super(NotClearableFileInput, self).render(name, value, attrs)

        if value and hasattr(value, "url"):
            template = self.template_with_initial
            substitutions['initial'] = format_html(self.url_markup_template,
                                               value.url,
                                               force_text(value))

        return mark_safe(template % substitutions)