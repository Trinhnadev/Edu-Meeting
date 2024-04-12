from django.db import models
from django.contrib.auth.models import User


class Role(models.Model):
    name = models.CharField(max_length=30)
    
    def __str__(self):
        return self.name
    
    def get_marketing_coordinator_role():
        return Role.objects.filter(name='marketing coordinator').first()

    @classmethod
    def create_default_role(cls):
        default_role, created = cls.objects.get_or_create(name='student')
        return default_role


class AcademicYear(models.Model):
    closure = models.DateTimeField()
    finalClosure = models.DateTimeField()

    def __str__(self):
        closure_date = self.closure.strftime('%Y-%m-%d')
        return f'Closure Date: {closure_date}'
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    fullname = models.CharField(max_length=50)
    roles = models.ManyToManyField(Role, related_name='users')
    
    faculty = models.ForeignKey('Faculties', on_delete=models.CASCADE, null=True, blank=True)
    
    email = models.EmailField(max_length=254, unique=True, blank=True, null=True)
    phone = models.CharField(max_length=15)
    activities_count = models.IntegerField(default=0)
    def get_activities_count(self):
        return self.activities.count()

    get_activities_count.short_description = 'Activities Count'
    

    def __str__(self):
        return self.fullname

    def save(self, *args, **kwargs):
        super(UserProfile, self).save(*args, **kwargs)  
        if not self.roles.exists():  
            default_role = Role.create_default_role()
            self.roles.add(default_role)

    def submit_assignment(request):
        profile = UserProfile.objects.get(user=request.user)
        profile.activities_count += 1
        profile.save()

class Faculties(models.Model):
    name = models.CharField(max_length = 40)
    description = models.TextField(null =True)
    def __str__(self):
        return self.name
    


class Room(models.Model):
    host = models.ForeignKey(UserProfile,on_delete=models.SET_NULL,null =True)
    topic = models.ForeignKey(Faculties,on_delete=models.SET_NULL,null=True)
    name = models.CharField(max_length=200,null =True)
    description = models.TextField(null = True, blank = True)
    participants = models.ManyToManyField(UserProfile,related_name='participants',blank=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(default=False) 
    question = models.CharField(max_length=200,null=True, blank=True) 
    answer = models.CharField(max_length=200,null=True, blank=True)

    class Meta:
        ordering = ['-updated','created']

    def __str__(seft):
        return seft.name
    
class RoomFile(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='files')
    uploaded_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    file = models.FileField(upload_to='room_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File {self.id} in room {self.room.name}"
    
class Message(models.Model):
    user = models.ForeignKey(UserProfile,on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    image = models.ImageField(blank=True, null=True)
    body = models.TextField()
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['updated','-created']
    def __str__(seft):
        return seft.body[0:50]
    


class Contributions(models.Model):
    user = models.ManyToManyField(UserProfile)
    title = models.CharField(max_length=100)
    content = models.TextField(null = True)
    faculty = models.ForeignKey(Faculties,on_delete=models.CASCADE)
    term = models.BooleanField(default=False)
    createAt = models.DateTimeField(auto_now_add=True)
    academic_Year = models.ForeignKey(AcademicYear,blank=True, null =True, on_delete=models.CASCADE)
    reject_reason = models.TextField(blank=True, null=True) 
    status = models.CharField(max_length=10,  default='waiting')
    public = models.BooleanField(default = False)
    def __str__(self):
        return self.title


class ContributionFiles(models.Model):
    word = models.FileField(null = True)
    img = models.FileField(null = True)
    contribution = models.ForeignKey(Contributions, on_delete=models.CASCADE, related_name='files', null=True)
    
    def __str__(self):
        return self.contribution.title if self.contribution else 'No Contribution'


class Comment(models.Model):
    user = models.ForeignKey(UserProfile,on_delete = models.CASCADE)
    contribution = models.ForeignKey(Contributions,on_delete = models.CASCADE)
    comment = models.TextField(blank=True,null=True)
    createAt = models.DateTimeField(auto_now_add=True)

    def __str__ (self):
        return f"{self.user.user.username} comment on {self.contribution}"

class PageView(models.Model):
    name = models.CharField(max_length=200,null =True)
    views = models.IntegerField(default=0)
    last_viewed = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
