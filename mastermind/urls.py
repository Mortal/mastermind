"""mastermind URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from mastermind.views import (
    Home, GameCreate, GameSubmission,
    GameAdmin, GameSlotCreate, GameUnconfirmedOptions,
)

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', Home.as_view(), name='home'),
    url(r'^game/new/$', GameCreate.as_view(), name='game_create'),
    url(r'^game/(?P<pk>\d+)/$', GameSubmission.as_view(),
        name='game_submission'),
    url(r'^game/(?P<pk>\d+)/admin/$', GameAdmin.as_view(), name='game_admin'),
    url(r'^game/(?P<pk>\d+)/admin/unconfirmed/$',
        GameUnconfirmedOptions.as_view(),
        name='game_unconfirmed_options'),
    url(r'^game/(?P<pk>\d+)/admin/slot/new/$', GameSlotCreate.as_view(),
        name='game_slot_create'),
]
