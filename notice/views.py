from xml.etree.ElementTree import Comment
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy, reverse

from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.shortcuts import redirect
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView
from crum import get_current_user

from .models import News, Event, Comment
from .forms import NewsForm, EventForm, CommentModelForm
from notice.models import create_comment
from planner.models import Task

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
    template_name = 'notice/comment_create.html'
    form_class = CommentModelForm
    success_message = 'Коментар додано'

    def form_valid(self, form):
        task = Task.objects.get(pk=self.kwargs['pk'])

        if not self.request.is_ajax():
            comment_text = self.request.POST.get("text")
            create_comment(get_current_user(), task, comment_text)
        return redirect(reverse('task_detail', args=[task.pk]))


class CommentUpdateView(BSModalUpdateView):
    model = Comment
    template_name = 'notice/comment_update.html'
    form_class = CommentModelForm
    success_message = 'Коментар оновлено'

    def get_success_url(self):
        comment = Comment.objects.get(pk=self.kwargs['pk'])
        return reverse('task_detail', args=[comment.object_id])


class CommentDeleteView(BSModalDeleteView):
    model = Comment
    template_name = 'notice/comment_delete.html'
    success_message = 'Коментар видалено'

    def get_success_url(self):
        comment = Comment.objects.get(pk=self.kwargs['pk'])
        return reverse('task_detail', args=[comment.object_id])
