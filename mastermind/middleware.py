from __future__ import absolute_import, unicode_literals, division

import functools

from django.utils.functional import SimpleLazyObject

from ipware.ip import get_real_ip

from mastermind.models import Profile


def get_profile(request):
    KEY = 'mastermind_profile_id'
    u = request.user if request.user.is_authenticated() else None

    if KEY in request.session:
        try:
            return Profile.objects.get(
                pk=int(request.session[KEY]),
                user=u)
        except Profile.DoesNotExist:
            pass

    if u:
        try:
            return Profile.objects.get(user=u)
        except Profile.DoesNotExist:
            pass


def get_or_create_profile(request):
    KEY = 'mastermind_profile_id'
    if request.profile:
        return request.profile
    p = Profile()
    if request.user.is_authenticated():
        p.user = request.user
    p.save()
    request.profile = p
    request.session[KEY] = p.pk
    return p


class Middleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.profile = SimpleLazyObject(functools.partial(
            get_profile, request))
        request.get_or_create_profile = functools.partial(
            get_or_create_profile, request)
        request.log_data = {'ip': get_real_ip(request)}
        return self.get_response(request)
