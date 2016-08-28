from django import forms


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
