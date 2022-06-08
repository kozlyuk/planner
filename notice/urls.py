from django.urls import path

from . import views


urlpatterns = [
    path('news/', views.NewsList.as_view(), name='news_list'),
    path('news/<int:pk>/detail/', views.NewsDetail.as_view(), name='news_detail'),
    path('news/<int:pk>/change/', views.NewsUpdate.as_view(), name='news_update'),
    path('news/add/', views.NewsCreate.as_view(), name='news_add'),
    path('news/<int:pk>/delete/', views.NewsDelete.as_view(), name='news_delete'),

    path('event/', views.EventList.as_view(), name='event_list'),
    path('event/<int:pk>/detail/', views.EventDetail.as_view(), name='event_detail'),
    path('event/<int:pk>/change/', views.EventUpdate.as_view(), name='event_update'),
    path('event/add/', views.EventCreate.as_view(), name='event_add'),
    path('event/<int:pk>/delete/', views.EventDelete.as_view(), name='event_delete'),

    path('comment/add/<int:task_pk>/', views.CommentCreateView.as_view(), name='comment_create'),
]
