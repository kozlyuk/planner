from django import forms
from bootstrap_modal_forms.forms import BSModalModelForm

from .models import News, Event, Comment


class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ['title', 'text', 'news_type', 'actual_from', 'actual_to']

    def __init__(self, *args, **kwargs):
        super(NewsForm, self).__init__(*args, **kwargs)
        self.fields['actual_from'].widget = forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'})
        self.fields['actual_to'].widget = forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'})
        self.fields['title'].widget.attrs.update({'style': 'width:100%;'})
        self.fields['text'].widget.attrs.update({'style': 'width:100%; height:63px;'})


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'date', 'repeat', 'description', 'is_holiday']

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.fields['date'].widget = forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'})
        self.fields['title'].widget.attrs.update({'style': 'width:100%;'})
        self.fields['description'].widget.attrs.update({'style': 'width:100%; height:63px;'})


class CommentModelForm(BSModalModelForm):
    class Meta:
        model = Comment
        fields = ['text']
