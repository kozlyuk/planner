from datetime import datetime
from django import forms

from django.conf.locale.uk import formats as uk_formats
date_format = uk_formats.DATE_INPUT_FORMATS[0]
time_format = uk_formats.TIME_INPUT_FORMATS[0]


class SplitDateTimeWidget(forms.SplitDateTimeWidget):
    """
    A widget that splits datetime input into two <input type="text"> boxes,
    and uses HTML5 'date' and 'time' inputs.
    """

    def __init__(self, attrs=None, date_format=None, time_format=None, date_attrs=None, time_attrs=None):
        date_attrs = date_attrs or {}
        time_attrs = time_attrs or {}
        if "type" not in date_attrs:
            date_attrs["type"] = "date"
        if "type" not in time_attrs:
            time_attrs["type"] = "time"
        return super().__init__(
            attrs=attrs, date_format=date_format, time_format=time_format, date_attrs=date_attrs, time_attrs=time_attrs
        )

    def decompress(self, value):
        if value:
            return [value.strftime('%Y-%m-%d'), value.strftime('%H:%M')]
        return [None, None]

    def value_from_datadict(self, data, files, name):
        date_str, time_str = super().value_from_datadict(data, files, name)
        # DateField expects a single string that it can parse into a date.

        if date_str == time_str == '':
            return None

        if time_str == '':
            time_str = '00:00'

        my_datetime = datetime.strptime(date_str + ' ' + time_str, "%Y-%m-%d %H:%M")
        # making timezone aware
        return my_datetime


class SplitDateTimeField(forms.SplitDateTimeField):
    widget = SplitDateTimeWidget
