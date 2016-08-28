import functools
from django.core.exceptions import ValidationError
from django.views.defaults import permission_denied
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect, get_object_or_404
# from django.urls import reverse
from mastermind.forms import (
    GameCreateForm, GameSlotCreateForm, GameUnconfirmedOptionsForm,
    GameSubmissionForm,
)
from mastermind.models import Game, Slot, Option, Submission


class Home(TemplateView):
    template_name = 'mastermind/home.html'

    def get_context_data(self, **kwargs):
        data = super(Home, self).get_context_data(**kwargs)
        if self.request.profile:
            data['my_games'] = self.request.profile.game_set.all()
        else:
            data['my_games'] = []
        data['games'] = Game.objects.all()
        return data


class GameCreate(FormView):
    form_class = GameCreateForm
    template_name = 'mastermind/gamecreateform.html'

    def form_valid(self, form):
        g = Game(owner=self.request.get_or_create_profile(),
                 title=form.cleaned_data['title'])
        g.save()
        return redirect('game_admin', pk=g.pk)


def single_game_decorator(require_admin):
    def decorator(cls):
        dispatch = cls.dispatch
        get_context_data = cls.get_context_data

        @functools.wraps(dispatch)
        def dispatch_wrapped(self, request, *args, **kwargs):
            super_func = dispatch.__get__(self, type(self))
            game = get_object_or_404(Game.objects, pk=kwargs.pop('pk'))
            has_access = (game.owner == request.profile or
                          request.user.is_superuser)
            if require_admin and not has_access:
                return permission_denied(request, exception=None)
            self.game = game
            return super_func(request, *args, **kwargs)

        @functools.wraps(get_context_data)
        def get_context_data_wrapped(self, **kwargs):
            super_func = get_context_data.__get__(self, type(self))
            data = super_func(**kwargs)
            data['game'] = self.game
            return data

        cls.dispatch = dispatch_wrapped
        cls.get_context_data = get_context_data_wrapped
        return cls

    return decorator


single_game = single_game_decorator(False)
single_game_admin = single_game_decorator(True)


@single_game_admin
class GameAdmin(TemplateView):
    template_name = 'mastermind/game_admin.html'


@single_game_admin
class GameSlotCreate(FormView):
    template_name = 'mastermind/game_slot_create.html'
    form_class = GameSlotCreateForm

    def form_valid(self, form):
        game = self.game
        pos = 1 + max((slot.position for slot in game.slot_set.all()),
                      default=0)
        slots = []
        for s in form.cleaned_data['stems']:
            slots.append(Slot(game=game, stem=s, position=pos))
            pos += 1
        Slot.objects.bulk_create(slots)
        return redirect('game_admin', pk=game.pk)


@single_game_admin
class GameUnconfirmedOptions(FormView):
    template_name = 'mastermind/game_unconfirmed_options.html'
    form_class = GameUnconfirmedOptionsForm

    def get_options(self):
        return Option.objects.filter(game=self.game, kind=Option.UNCONFIRMED)

    def get_form_kwargs(self, **kwargs):
        data = super(GameUnconfirmedOptions, self).get_form_kwargs(**kwargs)
        data['options'] = self.get_options()
        return data

    def form_valid(self, form):
        canonical_texts = {}
        for o in form.options:
            k = 'o-%s' % o.pk
            c = form.cleaned_data[k]
            if not c:
                continue
            canonical_texts[o] = c
        qs = Option.objects.filter(
            game=self.game, text__in=canonical_texts.values())
        existing = {o.text: o for o in qs}
        new_options = []
        errors = False
        save_options = []
        for o, c in canonical_texts.items():
            try:
                canonical = existing[c]
            except KeyError:
                if c == o.text:
                    o.kind = Option.CANONICAL
                    save_options.append(o)
                    continue
                else:
                    canonical = Option(
                        game=self.game, kind=Option.CANONICAL, text=c)
                    existing[c] = canonical
                    new_options.append(canonical)
            else:
                if o == canonical:
                    o.kind = Option.CANONICAL
                    save_options.append(o)
                    continue
            k = 'o-%s' % o.pk
            if canonical.is_alias:
                form.add_error(
                    k, '%s er et alias for %s' % (c, canonical.alias_target))
                errors = True
            elif canonical.is_unconfirmed:
                form.add_error(k, '%s er ubekræftet' % c)
                errors = True
            else:
                o.kind = Option.ALIAS
                o.alias_target = canonical
                save_options.append(o)
        if errors:
            return self.form_invalid(form)
        try:
            for o in new_options + save_options:
                o.clean()
        except ValidationError as exn:
            form.add_error(None, exn)
            return self.form_invalid(form)
        for o in new_options:
            o.save()
        for o in save_options:
            o.alias_target = o.alias_target
            o.save()
        return redirect('game_admin', pk=self.game.pk)


@single_game
class GameSubmission(FormView):
    form_class = GameSubmissionForm
    template_name = 'mastermind/game_submission.html'

    def get_form_kwargs(self, **kwargs):
        slots = self.game.slot_set.all()
        slots_initial = {}
        if self.request.profile:
            qs = Submission.objects.filter(
                profile=self.request.profile, slot__game=self.game)
            for s in qs:
                slots_initial[s.slot] = s.option.text
        data = super(GameSubmission, self).get_form_kwargs(**kwargs)
        data['game'] = self.game
        data['slots'] = slots
        data['slots_initial'] = slots_initial
        return data

    def form_valid(self, form):
        profile = self.request.get_or_create_profile()
        qs = Submission.objects.filter(
            profile=profile, slot__game=self.game)
        submission = {sub.slot: sub for sub in qs}
        for slot in form.slots:
            k = 's-%s' % slot.pk
            option = form.cleaned_data[k]
            if not option.pk:
                option.save()
            sub = submission.setdefault(slot, Submission(slot=slot,
                                                         profile=profile))
            sub.option = option
            sub.save()
        return redirect('game_submission', pk=self.game.pk)
