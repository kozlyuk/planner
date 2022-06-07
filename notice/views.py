from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from bootstrap_modal_forms.generic import BSModalCreateView

from .models import News, Event
from .forms import NewsForm, EventForm, CommentModelForm

@method_decorator(login_required, name='dispatch')
class NewsList(ListView):
    model = News
    success_url = reverse_lazy('home_page')


@method_decorator(login_required, name='dispatch')
class NewsDetail(DetailView):
    model = News
    success_url = reverse_lazy('news_list')


@method_decorator(login_required, name='dispatch')
class NewsCreate(CreateView):
    model = News
    form_class = NewsForm
    success_url = reverse_lazy('news_list')


@method_decorator(login_required, name='dispatch')
class NewsUpdate(UpdateView):
    model = News
    form_class = NewsForm
    success_url = reverse_lazy('news_list')


@method_decorator(login_required, name='dispatch')
class NewsDelete(DeleteView):
    model = News
    success_url = reverse_lazy('news_list')


@method_decorator(login_required, name='dispatch')
class EventList(ListView):
    model = Event
    success_url = reverse_lazy('home_page')


@method_decorator(login_required, name='dispatch')
class EventDetail(DetailView):
    model = Event


@method_decorator(login_required, name='dispatch')
class EventCreate(CreateView):
    model = Event
    form_class = EventForm
    success_url = reverse_lazy('event_list')


@method_decorator(login_required, name='dispatch')
class EventUpdate(UpdateView):
    model = Event
    form_class = EventForm
    success_url = reverse_lazy('event_list')


@method_decorator(login_required, name='dispatch')
class EventDelete(DeleteView):
    model = Event
    success_url = reverse_lazy('event_list')


class CommentCreateView(BSModalCreateView):
    template_name = 'notice/comment_form.html'
    form_class = CommentModelForm
    success_message = 'Коментар додано'
