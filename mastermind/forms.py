from django import forms
from mastermind.models import Option


class GameCreateForm(forms.Form):
    title = forms.CharField()


class GameSlotCreateForm(forms.Form):
    stems = forms.CharField(widget=forms.Textarea)

    def clean_stems(self):
        s = self.cleaned_data['stems']
        return s.splitlines()


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
        for s in self.slots:
            k = 's-%s' % s.pk
            try:
                v = self.cleaned_data[k]
            except KeyError:
                continue
            try:
                option = Option.objects.get(game=self.game, text=v)
            except Option.DoesNotExist:
                option = Option(
                    game=self.game, text=v, kind=Option.UNCONFIRMED)
            self.cleaned_data[k] = option
        return self.cleaned_data
