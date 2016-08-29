import functools
from django.core.exceptions import ValidationError
from django.views.defaults import permission_denied
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect, get_object_or_404
# from django.urls import reverse
from django.db.models import Count
from mastermind.forms import (
    GameCreateForm, GameUnconfirmedOptionsForm,
    GameSubmissionForm, GameAdminForm,
)
from mastermind.models import Game, Slot, Option, Submission, SubmissionSlot


class Home(TemplateView):
    template_name = 'mastermind/home.html'

    def get_context_data(self, **kwargs):
        data = super(Home, self).get_context_data(**kwargs)
        profile = self.request.profile
        if profile:
            own_games = profile.game_set.all()
            own_games = own_games.annotate(Count('submission'))
            my_submissions = profile.submission_set.all()
        else:
            own_games = []
            my_submissions = []
        data['own_games'] = own_games
        data['my_submissions'] = my_submissions
        data['games'] = Game.objects.filter(mode=Game.OPEN)
        data['game_create_form'] = GameCreateForm()
        return data


class GameCreate(FormView):
    form_class = GameCreateForm
    template_name = 'mastermind/game_create.html'

    def get_initial(self):
        return {'title': self.request.GET.get('title', '')}

    def form_valid(self, form):
        game = Game(owner=self.request.get_or_create_profile(),
                    title=form.cleaned_data['title'])
        game.save()
        slots = []
        for i, s in enumerate(form.cleaned_data['slots']):
            slots.append(Slot(game=game, stem=s, position=i + 1))
        Slot.objects.bulk_create(slots)
        options = []
        for o in form.cleaned_data['options']:
            options.append(Option(game=game, kind=Option.CANONICAL, text=o))
        Option.objects.bulk_create(options)
        return redirect('game_admin', pk=game.pk)


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
class GameAdmin(FormView):
    template_name = 'mastermind/game_admin.html'
    form_class = GameAdminForm

    def get_form_kwargs(self, **kwargs):
        data = super(GameAdmin, self).get_form_kwargs(**kwargs)
        data['game'] = self.game
        return data

    def form_valid(self, form):
        options = list(self.game.option_set.all())
        new_options = []
        for option_text in form.cleaned_data['new_options']:
            option = Option(game=self.game, text=option_text,
                            kind=Option.CANONICAL)
            option.clean()
            new_options.append(option)
        option_map = {o.text: o for o in options + new_options}
        for option in options:
            data = form.cleaned_option(option)
            target = data['alias_target']
            if target == '':
                option.kind = Option.UNCONFIRMED
            elif target == option.text:
                option.kind = Option.CANONICAL
            else:
                option.kind = Option.ALIAS
                option.alias_target = option_map[target]
            option.clean()

        slots = list(self.game.slot_set.all())
        for slot in slots:
            data = form.cleaned_slot(slot)
            slot.position = data['position']
            slot.stem = data['stem']
            if data['key']:
                slot.key = option_map[data['key']]
            else:
                slot.key = None

        next_position = len(slots) + 1

        for stem in form.cleaned_data['new_slots']:
            slots.append(Slot(
                game=self.game,
                position=next_position,
                stem=stem,
                key=None))

        for o in new_options + options:
            o.alias_target = o.alias_target  # Update alias_target_id
            o.save()
        for s in slots:
            s.key = s.key  # Update key_id
            s.save()

        self.game.mode = form.cleaned_data['mode']
        self.game.save()

        return redirect('game_admin', pk=self.game.pk)


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
            try:
                submission = Submission.objects.filter(
                    profile=self.request.profile, game=self.game).latest()
            except Submission.DoesNotExist:
                pass
            else:
                for s in submission.submissionslot_set.all():
                    slots_initial[s.slot] = s.option.text
        data = super(GameSubmission, self).get_form_kwargs(**kwargs)
        data['game'] = self.game
        data['slots'] = slots
        data['slots_initial'] = slots_initial
        return data

    def form_valid(self, form):
        profile = self.request.get_or_create_profile()
        submission = Submission(profile=profile, game=self.game)
        slots = []
        for slot in form.slots:
            k = 's-%s' % slot.pk
            option = form.cleaned_data[k]
            if not option.pk:
                option.save()
            slots.append(SubmissionSlot(submission=submission,
                                        slot=slot,
                                        option=option))
        submission.save()
        for s in slots:
            s.submission = s.submission  # Update submission_id
            s.save()
        return redirect('home')
