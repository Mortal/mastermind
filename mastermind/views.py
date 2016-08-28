import functools
from django.views.defaults import permission_denied
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect, get_object_or_404
# from django.urls import reverse
from mastermind.forms import (
    GameCreateForm, GameSlotCreateForm, GameUnconfirmedOptionsForm,
)
from mastermind.models import Game, Slot, Option


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


def game_admin(cls):
    dispatch = cls.dispatch
    get_context_data = cls.get_context_data

    @functools.wraps(dispatch)
    def dispatch_wrapped(self, request, *args, **kwargs):
        super_func = dispatch.__get__(self, type(self))
        game = get_object_or_404(Game.objects, pk=kwargs.pop('pk'))
        if game.profile != request.profile and not request.user.is_superuser:
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


@game_admin
class GameAdmin(TemplateView):
    template_name = 'mastermind/game_admin.html'


@game_admin
class GameSlotCreate(FormView):
    template_name = 'mastermind/game_slot_create.html'
    form_class = GameSlotCreateForm

    def form_valid(self, form):
        game = self.game
        next_position = 1 + max(slot.position for slot in game.slot_set.all())
        slots = []
        for s in form.cleaned_data['stems']:
            slots.append(Slot(game=game, stem=s, position=next_position))
            next_position += 1
        Slot.objects.bulk_create(slots)
        return redirect('game_admin', pk=game.pk)


@game_admin
class GameUnconfirmedOptions(FormView):
    template_name = 'mastermind/game_unconfirmed_options.html'
    form_class = GameUnconfirmedOptionsForm

    def get_options(self):
        return Option.objects.filter(game=self.game, kind=Game.UNCONFIRMED)

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
                    o.kind = Game.CANONICAL
                    save_options.append(o)
                    continue
                else:
                    canonical = Option(
                        game=self.game, kind=Game.CANONICAL, text=c)
                    existing[c] = canonical
                    new_options.append(canonical)
            if canonical.kind == Game.ALIAS:
                k = 'o-%s' % o.pk
                form.add_error(
                    k, '%s er et alias for %s' % (c, canonical.alias_target))
                errors = True
            o.kind = Game.ALIAS
            o.alias_target = canonical
            save_options.append(o)
        if errors:
            return self.form_invalid(form)
        for o in new_options:
            o.save()
        for o in save_options:
            o.alias_target = o.alias_target
            o.save()
        return redirect('game_admin', pk=self.game.pk)
