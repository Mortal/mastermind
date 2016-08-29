import collections
from django import forms
from mastermind.models import Option, Game
from mastermind.fields import DistinctLinesField


class GameCreateForm(forms.Form):
    title = forms.CharField()
    slots = DistinctLinesField()
    options = DistinctLinesField()


class GameUnconfirmedOptionsForm(forms.Form):
    def __init__(self, **kwargs):
        self.options = kwargs.pop('options')
        super(GameUnconfirmedOptionsForm, self).__init__(**kwargs)
        for o in self.options:
            k = 'o-%s' % o.pk
            self.fields[k] = forms.CharField(
                initial=o.text, label=o.text, required=False)


class GameSubmissionForm(forms.Form):
    def __init__(self, **kwargs):
        self.game = kwargs.pop('game')
        self.slots = kwargs.pop('slots')
        slots_initial = kwargs.pop('slots_initial')
        super(GameSubmissionForm, self).__init__(**kwargs)
        for s in self.slots:
            k = 's-%s' % s.pk
            self.fields[k] = forms.CharField(
                initial=slots_initial.get(s, ''), label=s.stem, required=False)

    def clean(self):
        options = {}
        for s in self.slots:
            k = 's-%s' % s.pk
            try:
                v = self.cleaned_data[k]
            except KeyError:
                continue
            if not v:
                self.cleaned_data[k] = None
                continue
            try:
                option = options[v]
            except KeyError:
                try:
                    option = Option.objects.get(game=self.game, text=v)
                except Option.DoesNotExist:
                    option = Option(
                        game=self.game, text=v, kind=Option.UNCONFIRMED)
                    option.clean()
                options[v] = option
            self.cleaned_data[k] = option
        return self.cleaned_data


class GameAdminForm(forms.Form):
    new_slots = DistinctLinesField(required=False)
    new_options = DistinctLinesField(required=False)

    def __init__(self, **kwargs):
        self.game = kwargs.pop('game')
        super(GameAdminForm, self).__init__(**kwargs)
        if self.game.mode == Game.INITIAL:
            mode_choices = Game.MODES
        else:
            mode_choices = [(k, v) for k, v in Game.MODES
                            if k != Game.INITIAL]
        self.fields['mode'] = forms.ChoiceField(
            choices=mode_choices, initial=self.game.mode)
        self.slot_keys = collections.OrderedDict()
        self.option_keys = collections.OrderedDict()
        for slot in self.game.slot_set.all():
            k = 's-%s' % slot.pk
            # Slot position
            self.fields[k + '-p'] = forms.IntegerField(
                initial=slot.position)
            # Slot stem
            self.fields[k + '-s'] = forms.CharField(
                initial=slot.stem)
            # Slot key
            key_initial = ''
            if slot.key:
                key_initial = slot.key.text
            self.fields[k + '-k'] = forms.CharField(
                initial=key_initial, required=False)
            self.slot_keys[k] = slot

        options = (
            o
            for kind in (Option.CANONICAL, Option.UNCONFIRMED, Option.ALIAS)
            for o in self.game.option_set.filter(kind=kind))

        for option in options:
            k = 'o-%s' % option.pk
            # Option alias target
            if option.kind == Option.CANONICAL:
                t = option.text
                r = True
            elif option.kind == Option.ALIAS:
                t = option.alias_target.text
                r = True
            elif option.kind == Option.UNCONFIRMED:
                t = ''
                r = False
            self.fields[k] = forms.CharField(initial=t, required=r)
            self.option_keys[k] = option

    def slots(self):
        return [
            dict(position=self[k + '-p'],
                 stem=self[k + '-s'],
                 key=self[k + '-k'])
            for k in self.slot_keys]

    def cleaned_slot(self, slot):
        k = 's-%s' % slot.pk
        return dict(position=self.cleaned_data[k + '-p'],
                    stem=self.cleaned_data[k + '-s'],
                    key=self.cleaned_data[k + '-k'])

    def game_options(self):
        return [
            dict(text=o.text,
                 alias_target=self[k])
            for k, o in self.option_keys.items()]

    def cleaned_option(self, option):
        k = 'o-%s' % option.pk
        return dict(alias_target=self.cleaned_data[k])

    def clean_new_slots(self):
        new_slots = set(self.cleaned_data['new_slots'])
        existing_slots = set(s.stem for s in self.slot_keys.values())
        e = ', '.join('"%s"' % v for v in new_slots & existing_slots)
        if e:
            self.add_error('new_slots', '%s findes allerede' % e)
        return self.cleaned_data['new_slots']

    def clean_new_options(self):
        new_options = set(self.cleaned_data['new_options'])
        existing_options = set(o.text for o in self.option_keys.values())
        e = ', '.join('"%s"' % v for v in new_options & existing_options)
        if e:
            self.add_error('new_options', '%s findes allerede' % e)
        return self.cleaned_data['new_options']

    def clean(self):
        has_all_positions = all(k + '-p' in self.cleaned_data
                                for k in self.slot_keys)
        if has_all_positions:
            # Clean slot positions
            slot_keys = list(self.slot_keys)
            # The stable sort ensures that multiple slots with same input pos.
            # are kept in the same order as they were before.
            slot_keys.sort(key=lambda k: self.cleaned_data[k + '-p'])
            for i, k in enumerate(slot_keys):
                self.cleaned_data[k + '-p'] = i + 1

        has_all_options = all(k in self.cleaned_data for k in self.option_keys)
        if has_all_options:
            # Clean alias targets
            alias_targets = {o.text: self.cleaned_data[k]
                             for k, o in self.option_keys.items()}

            for k, v in alias_targets.items():
                if v == '':
                    pass
                elif alias_targets.get(v, v) != v:
                    self.add_error('new_options',
                                   '"%s" peger på "%s" ' % (k, v) +
                                   'som ikke peger på sig selv')
                elif v not in alias_targets:
                    if v not in self.cleaned_data['new_options']:
                        # Add target as new option
                        self.cleaned_data['new_options'].append(v)

        has_all_keys = all(k + '-k' in self.cleaned_data
                           for k in self.slot_keys)
        has_new_options = 'new_options' in self.cleaned_data
        if has_all_keys and has_all_options and has_new_options:
            valid_options = (
                self.cleaned_data['new_options'] +
                [o.text for k, o in self.option_keys.items()
                 if self.cleaned_data[k] == o.text])
            invalid_options = [o.text for k, o in self.option_keys.items()
                               if self.cleaned_data[k] != o.text]
            for k in self.slot_keys:
                key = self.cleaned_data[k + '-k']
                if key:
                    if key in invalid_options:
                        self.add_error(k + '-k',
                                       '"%s" peger ikke på sig selv' % key)
                    elif key not in valid_options:
                        self.add_error(k + '-k',
                                       '"%s" er ikke en svarmulighed' % key)

        return self.cleaned_data
