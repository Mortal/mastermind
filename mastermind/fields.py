import collections
from django import forms
from django.utils.encoding import force_text
from django.core.exceptions import ValidationError
from django.forms.fields import Field


class DistinctLinesField(Field):
    widget = forms.Textarea

    def prepare_value(self, value):
        """Used by BoundField to display the value in a form."""
        if isinstance(value, (list, tuple)):
            return '\n'.join(value)
        else:
            return value

    def to_python(self, value):
        if not value:
            return []
        elif not isinstance(value, (list, tuple)):
            value = [line.strip() for line in force_text(value).splitlines()
                     if line.strip()]
        return value

    def validate(self, value):
        if not value and self.required:
            raise ValidationError(self.error_messages['required'],
                                  code='required')
        multi = []
        for k, v in collections.Counter(value).items():
            if v > 1:
                multi.append('"%s"' % (k,))
        if multi:
            raise ValidationError(
                '%s forekommer flere gange' % ', '.join(multi))

    def has_changed(self, initial, data):
        return tuple(initial) != tuple(data)
