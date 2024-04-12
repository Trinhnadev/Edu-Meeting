from django.contrib import admin

from .models import UserProfile,ContributionFiles,Contributions,Faculties,Role,AcademicYear,Comment, Room, RoomFile, PageView

admin.site.register(ContributionFiles)
admin.site.register(Contributions)
admin.site.register(Faculties)
admin.site.register(Role)
admin.site.register(AcademicYear)
admin.site.register(Comment)
admin.site.register(Room)
admin.site.register(RoomFile)
admin.site.register(PageView)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_activities_count']

    def get_activities_count(self, obj):
        return obj.activities.count()
    
    get_activities_count.short_description = 'Activities Count'





