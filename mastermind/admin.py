from django.contrib import admin
from mastermind.models import Profile, Game, Option, Slot, Submission


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('__str__',)


class GameAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'owner')


class OptionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'game')


class SlotAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'game')


class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'game', 'profile', 'created_time')


admin.site.register(Profile, ProfileAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(Option, OptionAdmin)
admin.site.register(Slot, SlotAdmin)
admin.site.register(Submission, SubmissionAdmin)
