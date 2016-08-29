from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Profile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200, blank=True, verbose_name='Navn')
    created_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.name:
            return '%s' % (self.name,)
        elif self.user:
            return '%s' % (self.user,)
        else:
            return '(profile %s)' % (self.pk,)


class Game(models.Model):
    INITIAL = 'initial'
    OPEN = 'open'
    CLOSED = 'closed'
    MODES = (
        (INITIAL, 'Ny'),
        (OPEN, 'Åben'),
        (CLOSED, 'Lukket'),
    )

    mode = models.CharField(max_length=20, choices=MODES, default=INITIAL)
    owner = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, blank=True, null=True)
    created_time = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100)

    def __str__(self):
        return '%s' % (self.title,)

    class Meta:
        verbose_name = 'spil'
        verbose_name_plural = verbose_name
        ordering = ['title']


class Option(models.Model):
    CANONICAL = 'canonical'
    ALIAS = 'alias'
    UNCONFIRMED = 'unconfirmed'
    KINDS = (
        (CANONICAL, 'Kanonisk'),
        (ALIAS, 'Alias'),
        (UNCONFIRMED, 'Ny'),
    )

    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    kind = models.CharField(
        max_length=20, choices=KINDS, verbose_name='slags')
    alias_target = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True)
    text = models.CharField(max_length=200, verbose_name='navn')

    @property
    def is_alias(self):
        return self.kind == Option.ALIAS

    @property
    def is_unconfirmed(self):
        return self.kind == Option.UNCONFIRMED

    def clean(self):
        if self.kind == Option.ALIAS:
            if not self.alias_target:
                raise ValidationError("Alias option must have target")
            elif self.game != self.alias_target.game:
                raise ValidationError("Alias option must target same game")
            elif self.alias_target == self:
                raise ValidationError(
                    "Alias option must not point to itself")
            elif self.alias_target.kind != Option.CANONICAL:
                raise ValidationError(
                    "Alias option must have canonical target")
        else:
            self.alias_target = None

    def __str__(self):
        if self.is_unconfirmed:
            return '%s?' % (self.text,)
        elif self.is_alias:
            if self.alias_target:
                return '%s -> %s' % (self.text, self.alias_target.text)
            else:
                return '%s -> %s' % (self.text, self.alias_target)
        else:
            return '%s' % (self.text,)

    class Meta:
        verbose_name = 'valgmulighed'
        verbose_name_plural = verbose_name + 'er'
        ordering = ['game', 'text']


class Slot(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    position = models.IntegerField()
    stem = models.CharField(max_length=200, verbose_name='navn')
    key = models.ForeignKey(
        Option, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return '%s' % (self.stem,)

    def clean(self):
        if self.key and self.game != self.key.game:
            raise ValidationError("Slot key must target same game")

    class Meta:
        verbose_name = 'indgang'
        verbose_name_plural = verbose_name + 'e'
        ordering = ['game', 'position']


class Submission(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    created_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        fields = (self.game, self.profile, self.created_time)
        return '<Submission for %s by %s on %s>' % fields

    class Meta:
        verbose_name = 'gæt'
        verbose_name_plural = verbose_name
        ordering = ['game', 'profile', 'created_time']


class SubmissionSlot(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE)
    option = models.ForeignKey(Option, on_delete=models.CASCADE)

    def clean(self):
        if self.slot.game != self.submission.game:
            raise ValidationError(
                "SubmissionSlot slot targets wrong game")
        if self.option.game != self.submission.game:
            raise ValidationError(
                "SubmissionSlot option targets wrong game")

    class Meta:
        verbose_name = 'gætindgang'
        verbose_name_plural = verbose_name + 'e'
        ordering = ['submission', 'slot']
        unique_together = [('submission', 'slot')]
