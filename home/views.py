
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect ,get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import ContributionFiles, Room, RoomFile, UserProfile, Faculties, Contributions, Role,AcademicYear, Comment,Room, Message, User, PageView
from django.contrib.auth.decorators import login_required

from .forms import CommentForm, FileForm, RoleForm, RoomForm
from django.urls import reverse
from io import BytesIO
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, F, ExpressionWrapper, fields
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q
from datetime import datetime, timedelta
from django.core.serializers.json import DjangoJSONEncoder
import zipfile
import re

def is_admins(user):
    return user.is_authenticated and user.userprofile.roles.filter(name='admin').exists()

def is_coordinators(user):
    return user.is_authenticated and user.userprofile.roles.filter(name='marketing coordinator').exists()

def is_managers(user):
    return user.is_authenticated and user.userprofile.roles.filter(name='marketing manager').exists()

def is_guests(user):
    return user.is_authenticated and user.userprofile.roles.filter(name='guest').exists()

def is_students(user):
    return user.is_authenticated and user.userprofile.roles.filter(name='student').exists()

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            is_first_login = user.last_login is None
            
            login(request, user)
            
            if is_first_login:
                messages.info(request, 'Welcome to Edu-Meeting! This appears to be your first login.', extra_tags='welcome')
            else:
                last_login_time = user.last_login.strftime('%Y-%m-%d %H:%M:%S')
                messages.info(request, f'Welcome back! You last logged in on {last_login_time}.', extra_tags='welcome_back')
                
            return redirect('home')
        else:
           messages.error(request, 'Login failed. Please check your username and password.', extra_tags='login_error')

    return render(request, 'login.html')

def register_view(request):
    faculties = Faculties.objects.all()

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        fullname = request.POST.get('fullname')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        repassword = request.POST.get('repassword')
        faculty_id = request.POST.get('faculty', None)

        if all([username, fullname, phone, password, repassword]):
            password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
            if password == repassword:
                if not re.match(password_pattern, password):
                    return render(request, 'register.html', {
                        'faculties': faculties,
                        'error_message': 'Password must include at least one lowercase letter, one uppercase letter, one special character, and one number.'
                    })
                if User.objects.filter(username=username).exists():
                    messages.error(request, 'Username already exists!', extra_tags='username_exist')
                    return redirect('register')
                else:
                    user = User.objects.create_user(username=username, password=password, email=email)
                    faculty = Faculties.objects.get(id=faculty_id) if faculty_id else None
                    
                    userprofile = UserProfile.objects.create(user=user, fullname=fullname, email=email, phone=phone, faculty=faculty)
                    return redirect('login')
            else:
                messages.error(request, 'Confirm password do not match', extra_tags='password_notmatch')
                return redirect('register')
        
    return render(request, 'register.html', {'faculties': faculties})


def logout_view(request):
    logout(request)
    return redirect('home')


def get_user_roles_and_permissions(user):
    permissions = {
        'can_upload': True,
        'is_admin': False,
        'is_coordinator': False,
        'is_manager': False,
        'is_student': False,
        'is_guest': False,
        'show_faculties': True,
        'faculties': Faculties.objects.none(),
    }

    if user.is_authenticated:
        try:
            user_profile = user.userprofile
            faculty = user_profile.faculty
            roles = [role.name for role in user_profile.roles.all()]

            if "marketing manager" in roles:
                permissions.update({
                    'faculties': Faculties.objects.all(),
                    'is_manager': True
                })
            elif "admin" in roles:
                permissions.update({
                    'faculties': Faculties.objects.all(),
                    'is_admin': True
                })
            elif "marketing coordinator" in roles:
                permissions['faculties'] = Faculties.objects.filter(id=faculty.id) if faculty else Faculties.objects.none()
                permissions['is_coordinator'] = True
            elif "guest" in roles:
                permissions['faculties'] = Faculties.objects.filter(id=faculty.id) if faculty else Faculties.objects.none()
                permissions['is_guest'] = True
            else:
                permissions.update({
                    'is_student': True,
                    'show_faculties': False
                })

        except UserProfile.DoesNotExist:
            permissions.update({
                'can_upload': True,
                'show_faculties': False
            })
    else:
        permissions['show_faculties'] = False

    return permissions

def home(request):
    permissions = get_user_roles_and_permissions(request.user)
    public_contributions = Contributions.objects.filter(public=True)

    context = {
        'faculties': permissions['faculties'],
        'can_upload': permissions['can_upload'],
        'is_admin': permissions['is_admin'],
        'is_coordinator': permissions['is_coordinator'],
        'is_manager': permissions['is_manager'],
        'is_student': permissions['is_student'],
        'is_guest': permissions['is_guest'],
        'show_faculties': permissions['show_faculties'],
        'public_contributions': public_contributions,
    }
    return render(request, 'home.html', context)



def file_upload_view(request):
    if not is_students(request.user):
        return redirect('error_404')

    faculties = None 
    
    if request.user.is_authenticated:
        user_profile = None
        faculties = None
        try:
            user_profile = request.user.userprofile
            is_student = True
            faculties = Faculties.objects.filter(id=user_profile.faculty.id)
            valid_academic_years = AcademicYear.objects.filter(closure__gt=timezone.now())
        except UserProfile.DoesNotExist:
            pass
        
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        faculty_id = request.POST.get('faculty')
        academicYear = request.POST.get('academic')

        term = request.POST.get('term') == 'on'

        for file in request.FILES.getlist('word') + request.FILES.getlist('img'):
            if file.name.endswith('.pdf'):
                messages.error(request, 'You can only upload document files end with .doc or .docx')
                return redirect('file_upload') 

        try:
            faculty = Faculties.objects.get(id=faculty_id)
            academic_year = AcademicYear.objects.get(id=academicYear)

            contribution = Contributions.objects.create(
                title=title,
                content=content,
                faculty=faculty,
                term=term,
                academic_Year=academic_year
            )
            contribution.user.add(request.user.userprofile)

            contribution_file = ContributionFiles(contribution=contribution)
            for file in request.FILES.getlist('word') + request.FILES.getlist('img'):
                if file.name.endswith('.doc') or file.name.endswith('.docx'):
                    if not contribution_file.word:
                        contribution_file.word = file
                elif not file.name.endswith('.pdf') and not contribution_file.img:
                    contribution_file.img = file

            contribution_file.save()

            #sendmail
            marketing_coordinator_role = Role.get_marketing_coordinator_role()
            if marketing_coordinator_role:
                coordinator_profiles = UserProfile.objects.filter(
                    roles=marketing_coordinator_role,
                    faculty=faculty
                )

                recipient_list = [coordinator.email for coordinator in coordinator_profiles if coordinator.email]
                if recipient_list:
                    send_mail(
                        subject='New Contribution Submitted', message=f'A new contribution "{title}" has been submitted to {faculty.name} by {request.user.userprofile.fullname}.',
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=recipient_list,
                    )

            return redirect('success_url') 
        except Faculties.DoesNotExist:
            return redirect('home')
        except Exception as e:
            print(e) 
            return redirect('home')

    
    else:
        context = {'faculties': faculties,
                   'is_student': is_student,
                   'valid_academic_years':valid_academic_years}
        
    return render(request, 'upload.html', context)

def update_contribution(request, pk):
    if not is_students(request.user):
        return redirect('error_404')

    contribution = get_object_or_404(Contributions, pk=pk)

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        term = request.POST.get('term') == 'on'
        contribution.title = title
        contribution.content = content
        contribution.term = term
        contribution.status = "waiting"
        contribution.save()

        word_file = request.FILES.get('word', None)
        img_file = request.FILES.get('img', None)
        if word_file or img_file:
            contribution_files, created = ContributionFiles.objects.get_or_create(contribution=contribution)
            if word_file:
                contribution_files.word = word_file
            if img_file:
                contribution_files.img = img_file
            contribution_files.save()

        return redirect('my_contributions')  

    contribution_files = ContributionFiles.objects.filter(contribution=contribution).first()
    context = {
        'contribution': contribution,
        'contribution_files': contribution_files,
    }
    return render(request, 'update_contribution.html', context)

@login_required
def delete_contribution(request, pk):
    if not is_students(request.user):
        return redirect('error_404')

    contribution = get_object_or_404(Contributions, pk=pk)
    if request.method == 'GET': 
        contribution.delete()
        return redirect('my_contributions')
    else:
        return HttpResponse('Method not allowed', status=405) 


def upload_success(request):
    if not is_students(request.user):
        return redirect('error_404')

    is_student = True
    show_faculties = True
    context = {
        'is_student': is_student,
        'show_faculties': show_faculties
    }
    return render(request, 'upload_success.html', context)

def create_account(request):
    if not is_admins(request.user):
        return redirect('error_404')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        fullname = request.POST['fullname']
        phone = request.POST.get('phone', '')
        role_id = request.POST['role']
        faculty_id = request.POST.get('faculty', None) 

        if password == confirm_password:
            user = User.objects.create_user(username=username, password=password)

            new_profile = UserProfile(user=user, fullname=fullname, phone=phone)

            if faculty_id:
                try:
                    faculty = Faculties.objects.get(id=faculty_id)
                    new_profile.faculty = faculty
                except Faculties.DoesNotExist:
                    pass  

            new_profile.save()

            selected_role = Role.objects.get(id=role_id)
            new_profile.roles.add(selected_role)

            return redirect('account_list')
    else: 
        roles = Role.objects.all()
        faculties = Faculties.objects.all() 
        return render(request, 'create_account.html', {'roles': roles, 'faculties': faculties})




def faculty_files(request, faculty_id):
    if not is_coordinators(request.user) and not is_guests(request.user):
        return redirect('error_404')

    is_guest = False
    is_manager = False
    is_coordinator = False
    user_profile = get_object_or_404(UserProfile, user=request.user)
    show_faculties = True 
    faculty = user_profile.faculty
    faculties = Faculties.objects.none() 
    contributions = Contributions.objects.filter(faculty_id=faculty_id)
    for contribution in contributions:
        contribution.comments = Comment.objects.filter(contribution=contribution)


    if request.user.is_authenticated:
        roles = [role.name for role in user_profile.roles.all()]

        if "marketing manager" in roles:
            is_manager = True
            faculties = Faculties.objects.all() 
        elif "marketing coordinator" in roles:
            is_coordinator = True
            faculties = Faculties.objects.filter(id=faculty.id) if faculty else Faculties.objects.none()
        elif "guest" in roles:
            is_guest = True
            faculties = Faculties.objects.all() 
            contributions = Contributions.objects.filter(faculty_id=faculty_id, status="approved")

        if "marketing coordinator" in roles and (timezone.now() - contribution.createAt).days > 14:
            can_comment = False
        else:
            can_comment = True

    faculty = get_object_or_404(Faculties, pk=faculty_id)
    files = ContributionFiles.objects.filter(contribution__in=contributions).distinct()
    comment_form = CommentForm()   
    dayCanComment = 14 - (timezone.now() - contribution.createAt).days

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            contribution_id = request.POST.get('contribution_id')
            try:
                contribution = Contributions.objects.get(id=contribution_id)
                new_comment = comment_form.save(commit=False)
                new_comment.contribution = contribution

                user_profile, created = UserProfile.objects.get_or_create(user=request.user)
                new_comment.user = user_profile
                new_comment.save()
                return redirect('faculty_files', faculty_id=faculty_id)
            except Contributions.DoesNotExist:
                return HttpResponse("Contribution does not exist", status=404)
    return render(request, 'faculty_file.html', {'faculty': faculty, 
                                                 'files': files, 
                                                 'is_guest': is_guest,
                                                 'contributions': contributions,
                                                 'faculties': faculties,
                                                 'show_faculties': show_faculties,
                                                 'is_manager': is_manager,
                                                 'is_coordinator': is_coordinator,
                                                 'can_comment': can_comment,
                                                 'dayCanComment': dayCanComment,})
                                                 
def download_selected_contributions(request):
    if not is_managers(request.user):
        return redirect('error_404')
    
    contribution_ids = request.POST.getlist('contribution_ids')
    files = ContributionFiles.objects.filter(contribution__id__in=contribution_ids)

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            if file.word:
                zip_file.write(file.word.path, arcname=file.word.name)
            if file.img:
                zip_file.write(file.img.path, arcname=file.img.name)

    zip_buffer.seek(0)

    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="selected_contributions.zip"'

    return response


def update_profile(request):
    user_profile = get_object_or_404(UserProfile, user=request.user.userprofile)
    show_faculties = True 
    faculty = user_profile.faculty
    faculties = Faculties.objects.none() 
    is_coordinator = False
    is_manager = False
    is_student = False

    if request.user.is_authenticated:
        roles = [role.name for role in user_profile.roles.all()]

        if "marketing manager" in roles:
            faculties = Faculties.objects.all()
            is_manager = True
        elif "marketing coordinator" in roles:
            faculties = Faculties.objects.filter(id=faculty.id) if faculty else Faculties.objects.none()
            is_coordinator = True
        else:
            is_student = True

    if request.method == 'POST':
        user_profile.fullname = request.POST.get('fullname', '')
        user_profile.email = request.POST.get('email', '')
        user_profile.phone = request.POST.get('phone', '')
        user_profile.save()
        return redirect('home')
    else:
        return render(request, 'update_profile.html', {'user_profile': user_profile,
                                                       'faculties': faculties,
                                                       'show_faculties': show_faculties,
                                                       'is_coordinator': is_coordinator,
                                                       'is_manager': is_manager,
                                                       'is_student': is_student})

def contributions_detail(request, contribution_id):
    if is_guests(request.user):
        return redirect('error_404')
    
    contribution = get_object_or_404(Contributions, id=contribution_id)
    comments = Comment.objects.filter(contribution=contribution)
    user_profile = request.user.userprofile
    show_faculties = True 
    faculties = Faculties.objects.none() 
    faculty = user_profile.faculty
    is_coordinator = False
    is_student = False 
    is_manager = False 
    
    if request.user.is_authenticated:
        roles = [role.name for role in user_profile.roles.all()]

        if "marketing coordinator" in roles:
            faculties = Faculties.objects.filter(id=faculty.id) if faculty else Faculties.objects.none()
            is_coordinator = True
        elif "marketing manager" in roles:
            faculties = Faculties.objects.all()
            is_manager = True
        else:
            is_student = True
            show_faculties = False

        if "marketing coordinator" in roles and (timezone.now() - contribution.createAt).days > 14:
            can_comment = False
        else:
            can_comment = True

        academic_year = contribution.academic_Year
        if academic_year:
            contribution.is_expired = timezone.now() > academic_year.finalClosure


    if request.method == "POST":
        if 'comment' in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                new_comment = comment_form.save(commit=False)
                new_comment.contribution = contribution
                new_comment.user = request.user.userprofile
                new_comment.save()
                return HttpResponseRedirect(reverse('contributions_detail', args=[contribution_id]))

        elif request.FILES:
            file_form = FileForm(request.POST, request.FILES)
            if file_form.is_valid():
                new_file = file_form.save(commit=False)
                new_file.contribution = contribution
                new_file.save()
                return HttpResponseRedirect(reverse('contributions_detail', args=[contribution_id]))
    else:
        comment_form = CommentForm()
        file_form = FileForm()

    dayCanComment = 14 - (timezone.now() - contribution.createAt).days

    return render(request, 'contributions_detail.html', {
        'contribution': contribution,
        'comments': comments,
        'comment_form': comment_form,
        'file_form': file_form,
        'show_faculties': show_faculties,
        'is_coordinator': is_coordinator,
        'is_student': is_student,
        'is_manager': is_manager,
        'faculties': faculties,
        'can_comment': can_comment,
        'dayCanComment': dayCanComment,
    })    



def my_contributions(request):
    if not is_students(request.user):
        return redirect('error_404')
    
    is_student = True
    can_update = True
    user_profile = UserProfile.objects.get(user=request.user)
    contributions = Contributions.objects.filter(user=user_profile).prefetch_related('faculty', 'files')
    
    if request.user.is_authenticated:
        for contribution in contributions:
            academic_year = contribution.academic_Year
            if academic_year:
                contribution.is_expired = timezone.now() > academic_year.finalClosure

    context = {
        'contributions': contributions,
        'is_student': is_student
    }
    return render(request, 'my_contribution.html', context)



def list_faculties(request):
    if not is_admins(request.user):
        return redirect('error_404')
    
    faculties = Faculties.objects.all()
    return render(request, 'list_faculties.html', {'faculties': faculties})


def remove_faculty(request, faculty_id):
    if not is_admins(request.user):
        return redirect('error_404')
    
    faculty = get_object_or_404(Faculties, pk=faculty_id)
    faculty.delete()
    return redirect('list_faculties')



@login_required
def user_profile(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    show_faculties = True 
    faculty = user_profile.faculty
    faculties = Faculties.objects.none() 
    is_coordinator = False
    is_manager = False
    is_student = False

    if request.user.is_authenticated:
        roles = [role.name for role in user_profile.roles.all()]

        if "marketing manager" in roles:
            faculties = Faculties.objects.all()
            is_manager = True
        elif "marketing coordinator" in roles:
            faculties = Faculties.objects.filter(id=faculty.id) if faculty else Faculties.objects.none()
            is_coordinator = True
        else:
            is_student = True
            show_faculties = False

    return render(request, 'profile.html', {'user_profile': user_profile,
                                            'faculties': faculties,
                                            'show_faculties': show_faculties,
                                            'is_coordinator': is_coordinator,
                                            'is_manager': is_manager,
                                            'is_student': is_student})

def list_academic_years(request):
    if not is_admins(request.user):
        return redirect('error_404')
    
    academic_years = AcademicYear.objects.all()
    return render(request, 'list_academic_years.html', {'academic_years': academic_years})


def create_academic_year(request):
    if not is_admins(request.user):
        return redirect('error_404')

    page = "create"
    if request.method == "POST":
        closure = request.POST.get('closure')
        finalClosure = request.POST.get('finalClosure')
        AcademicYear.objects.create(closure=closure, finalClosure=finalClosure)
        return redirect('list_academic_years')
    context = {
        'page' : page,
    }
    return render(request, 'academic_years_form.html', context)


def update_academic_year(request, year_id):
    if not is_admins(request.user):
        return redirect('error_404')
    
    page = "update"
    academic_year = get_object_or_404(AcademicYear, pk=year_id)
    if request.method == "POST":
        academic_year.closure = request.POST.get('closure')
        academic_year.finalClosure = request.POST.get('finalClosure')
        academic_year.save()
        return redirect('list_academic_years')
    context = {
        'page' : page,
        'academic_year': academic_year,
    }
    return render(request, 'academic_years_form.html', context)


def remove_academic_year(request, year_id):
    if not is_admins(request.user):
        return redirect('error_404')
    
    academic_year = get_object_or_404(AcademicYear, pk=year_id)
    academic_year.delete()
    return redirect('list_academic_years')


def create_faculty(request):
    if not is_admins(request.user):
        return redirect('error_404')
    
    page = "create"
    if request.method == "POST":
        name = request.POST.get('name')
        description = request.POST.get('description')
        Faculties.objects.create(name=name, description=description)
        return redirect('list_faculties')
    academic_years = AcademicYear.objects.all()
    context = {
        'page' : page,
        'academic_years': academic_years
    }
    return render(request, 'faculties_form.html', context)


def update_faculty(request, faculty_id):
    if not is_admins(request.user):
        return redirect('error_404')
    
    page = "update"
    faculty = get_object_or_404(Faculties, pk=faculty_id)
    if request.method == "POST":
        faculty.name = request.POST.get('name')
        faculty.description = request.POST.get('description')
        faculty.save()
        return redirect('list_faculties')
    academic_years = AcademicYear.objects.all()
    context = {
        'page' : page,
        'faculty': faculty, 
        'academic_years': academic_years
    }
    return render(request, 'faculties_form.html', context)

def create_role(request):
    if not is_admins(request.user):
        return redirect('error_404')
    
    if request.method == "POST":
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('role_list')
    else:
        form = RoleForm()
    return render(request, 'create_role.html', {'form': form})

def role_list(request):
    if not is_admins(request.user):
        return redirect('error_404')
    
    roles = Role.objects.all()
    return render(request, 'role_list.html', {'roles': roles})

def delete_role(request, role_id):
    if not is_admins(request.user):
        return redirect('error_404')
    
    role = get_object_or_404(Role, id=role_id)
    role.delete()
    return redirect('role_list') 


def all_contributions_view(request):
    if not is_coordinators(request.user) and not is_managers(request.user):
        return redirect('error_404')
    
    user_profile = get_object_or_404(UserProfile, user=request.user)
    contributions = Contributions.objects.all()
    is_coordinator = False
    is_manager = False
    faculty = user_profile.faculty
    
    if request.user.is_authenticated:
        roles = [role.name for role in user_profile.roles.all()]

        if "marketing manager" in roles:
            is_manager = True
            contributions = Contributions.objects.filter(status="approved")
        else:
            is_coordinator = True
            contributions = Contributions.objects.filter(faculty=faculty)

    query = request.GET.get('q')
    if query:
        contributions = contributions.filter(
            Q(user__fullname__icontains=query) |
            Q(title__icontains=query)  
        )

    all_academic_years = AcademicYear.objects.all()

    academic_year_id = request.GET.get('academic_year')
    if academic_year_id:
        contributions = contributions.filter(academic_Year_id=academic_year_id)

    context = {
        'contributions': contributions,
        'is_manager': is_manager,
        'is_coordinator': is_coordinator,
        'all_academic_years': all_academic_years,
    }
    return render(request, 'manage_contributions.html', context)

    
def account_list(request):
    if not is_admins(request.user):
        return redirect('error_404')
    
    accounts = UserProfile.objects.all()
    return render(request, 'listAccount.html', {'accounts': accounts})

def account_update(request, pk):
    if not is_admins(request.user):
        return redirect('error_404')
    
    user_profile = get_object_or_404(UserProfile, pk=pk)

    if request.method == 'POST':
        user_profile.fullname = request.POST.get('fullname')
        user_profile.email = request.POST.get('email')
        user_profile.phone = request.POST.get('phone')

        faculty_id = request.POST.get('faculty')
        if faculty_id:
            user_profile.faculty = Faculties.objects.get(id=faculty_id)
        else:
            user_profile.faculty = None

        user_profile.save()

        selected_roles = request.POST.getlist('roles')
        user_profile.roles.clear()
        for role_id in selected_roles:
            role = Role.objects.get(id=role_id)
            user_profile.roles.add(role)

        return redirect('account_list')
    else:
        faculties = Faculties.objects.all()
        roles = Role.objects.all()
        return render(request, 'editAccount.html', {
            'user_profile': user_profile,
            'faculties': faculties,
            'roles': roles
        })

def account_delete(request, pk):
    if not is_admins(request.user):
        return redirect('error_404')
    
    if request.method == 'GET':
        account = get_object_or_404(User, pk=pk)
        account.delete()
        return redirect('account_list')

import json
def statistical_analysis(request):
    if is_students(request.user):
        return redirect('error_404')
    user_profile = get_object_or_404(UserProfile, user=request.user)
    is_coordinator = False
    is_manager = False
    is_guest = False
    is_admin = False
    total_students = 0
    total_contribution = 0

    academic_years = AcademicYear.objects.all().order_by('-closure')

    contributions_by_faculty_year = Contributions.objects.values('faculty__name', 'academic_Year__id').annotate(total=Count('id')).order_by()

    contributions_data = {}
    for item in contributions_by_faculty_year:
        faculty_name = item['faculty__name']
        year_id = item['academic_Year__id']
        contributions_count = item['total']
        if faculty_name not in contributions_data:
            contributions_data[faculty_name] = {}
        contributions_data[faculty_name][year_id] = contributions_count
    
    if request.user.is_authenticated:
        roles = [role.name for role in user_profile.roles.all()]

        if "marketing manager" in roles:
            is_manager = True
        elif "marketing coordinator" in roles:
            is_coordinator = True
        elif "guest" in roles:
            is_guest = True
        elif "admin" in roles:
            is_admin = True

    user_contributions = UserProfile.objects.annotate(total_contributions=Count('contributions')).values('fullname', 'total_contributions')

    user_labels = [item['fullname'] for item in user_contributions]
    contributions_by_user = [item['total_contributions'] for item in user_contributions]

    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    contributions_over_time = Contributions.objects.filter(createAt__range=(start_date, end_date)).values('createAt__date').annotate(total=Count('id'))

    time_labels = [item['createAt__date'].strftime('%Y-%m-%d') for item in contributions_over_time]
    contributions_counts = [item['total'] for item in contributions_over_time]

    #2
    total_contributions = Contributions.objects.count()
    approved_contributions = Contributions.objects.filter(status="approved").count()
    waiting_contributions = Contributions.objects.filter(status="waiting").count()
    rejected_contributions = Contributions.objects.filter(status="rejected").count()

    total_status_percentages = {
        'Approved': (approved_contributions / total_contributions) * 100,
        'Waiting': (waiting_contributions / total_contributions) * 100,
        'Rejected': (rejected_contributions / total_contributions) * 100
    }

    if is_guest:
        guest_faculty = user_profile.faculty.name
        contributions_by_faculty = Contributions.objects.filter(faculty__name=guest_faculty).values('faculty__name').annotate(total=Count('id'))
    else:
        contributions_by_faculty = Contributions.objects.values('faculty__name').annotate(total=Count('id'))
    approved_by_faculty = Contributions.objects.filter(status="approved").values('faculty__name').annotate(total=Count('id'))

    faculty_names = [item['faculty__name'] for item in contributions_by_faculty]
    contributions_counts = [item['total'] for item in contributions_by_faculty]
    approved_counts = [item['total'] for item in approved_by_faculty]

    page_views = PageView.objects.all().order_by('-views')[:10]  
    active_users = UserProfile.objects.all().order_by('-activities_count')[:10]  

    page_views_data = {
        "labels": [pv.name for pv in page_views],
        "data": [pv.views for pv in page_views],
    }

    active_users_data = {
        "labels": [up.user.username for up in active_users],
        "data": [up.activities_count for up in active_users],
    }

    student_accounts = UserProfile.objects.filter(roles__name='student').annotate(contributions_count=Count('contributions')).filter(contributions_count__gt=0)
    
    student_accounts_with_contributions = UserProfile.objects.filter(roles__name='student', contributions__isnull=False).distinct()

    faculty_accounts = student_accounts_with_contributions.values('faculty__name').annotate(total=Count('user', distinct=True))

    faculty_namess = [item['faculty__name'] for item in faculty_accounts]
    faculty_countss = [item['total'] for item in faculty_accounts]



    #4 
    contributions_with_comments = Contributions.objects.filter(comment__isnull=False).values('faculty__name').annotate(total=Count('id'))
    contribution_percentages_with_comments = {}
    for item in contributions_by_faculty:
        faculty_name = item['faculty__name']
        total = item['total']
        with_comments = next((i['total'] for i in contributions_with_comments if i['faculty__name'] == faculty_name), 0)

        contribution_percentages_with_comments[faculty_name] = with_comments

    #5
    contributions_without_comments = Contributions.objects.filter(comment__isnull=True).values('faculty__name').annotate(total=Count('id'))

    contribution_percentages_without_comments = {}
    for item in contributions_by_faculty:
        faculty_name = item['faculty__name']
        total = item['total']
        without_comments = next((i['total'] for i in contributions_without_comments if i['faculty__name'] == faculty_name), 0)
        
        if total > 0:
            percentage_without_comments = without_comments
        else:
            percentage_without_comments = 0
        
        contribution_percentages_without_comments[faculty_name] = percentage_without_comments

    #6   
    if is_coordinator:
        coordinator_faculty = user_profile.faculty
        total_students = UserProfile.objects.filter(faculty=coordinator_faculty, roles__name='student').count()

    #7
    if is_coordinator:
        total_contribution = Contributions.objects.filter(faculty=coordinator_faculty).count()

    #8
    now = timezone.now()
    fourteen_days_ago = now - timedelta(days=14)

    contributions_no_comment_after_14_days = Contributions.objects.filter(
        createAt__lte=fourteen_days_ago,
        comment__isnull=True
    ).values('faculty__name').annotate(total=Count('id')).order_by('faculty__name')

    contributions_no_comment_after_14_days_data = json.dumps(list(contributions_no_comment_after_14_days), cls=DjangoJSONEncoder)


    context = {
        'contributions_no_comment_after_14_days_data': contributions_no_comment_after_14_days_data,
        'total_students': total_students,
        'total_contribution': total_contribution,
        'contributions_without_comments_data': json.dumps(contribution_percentages_without_comments),
        'comments_by_faculty_percentages': contribution_percentages_with_comments,
        'total_status_percentages': total_status_percentages,
        'faculty_namess': faculty_namess,
        'faculty_countss': faculty_countss,
        'academic_years': academic_years,
        'contributions_data': contributions_data,
        'user_labels': user_labels,
        'contributions_by_user': contributions_by_user,
        'time_labels': time_labels,
        'contributions_over_time': contributions_counts,
        'total_contributions': total_contributions,
        'approved_contributions': approved_contributions,
        'faculty_names': faculty_names,
        'contributions_by_faculty': contributions_counts,
        'approved_by_faculty': approved_counts,
        'page_views_data': json.dumps(page_views_data),
        'active_users_data': json.dumps(active_users_data),
        'is_manager': is_manager,
        'is_coordinator': is_coordinator,
        'is_guest': is_guest,
        'is_admin': is_admin,
    }
    return render(request, 'statistical_analysis.html', context)

def approve_contribution(request, contribution_id):
    if not is_coordinators(request.user):
        return redirect('error_404')
    
    contribution = get_object_or_404(Contributions, id=contribution_id)
    approve = request.GET.get('approve')

    if request.method == "GET":
        if approve == "app": 
            contribution.status ='approved'
        elif approve == "dis": 
            contribution.status ='waiting'
    contribution.save()
    return redirect('manage_contributions')

def public_contribution(request, contribution_id):
    if not is_managers(request.user):
        return redirect('error_404')
    
    contribution = get_object_or_404(Contributions, id=contribution_id)
    public = request.GET.get('public')
    
    
    if request.method == "GET":
        if public == "pub":  
            contribution.public = True
        elif public == "non":  
            contribution.public = False
        contribution.save()
        return redirect('manage_contributions')
    else:
        return redirect('home')  

@csrf_protect
def reject_contribution(request, contribution_id):
    if not is_coordinators(request.user):
        return redirect('error_404')
    
    if request.method == "POST":
        contribution = get_object_or_404(Contributions, id=contribution_id)
        reject_reason = request.POST.get("reject_reason")
        contribution.reject_reason = reject_reason

        user_profiles = contribution.user.all()
        recipient_list = [user.email for user in user_profiles if user.email]
        if recipient_list:
            send_mail(
                subject='Contribution Rejected',
                message=f'Your contribution "{contribution.title}" has been rejected for the following reason: {reject_reason}',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=recipient_list,
            )

        contribution.status = 'rejected'
        contribution.save()
        return redirect('manage_contributions')
    else:
        return redirect('home')
    
def term_policy(request):
    return render(request, 'terms_policies.html')

    
def error_404(request):
    return render(request, '404.html')





@login_required
def room(request,pk):
    if is_admins(request.user) or is_guests(request.user):
        return redirect('error_404')
    
    room = Room.objects.get(id=pk)
    pa = room.participants.all()
    messages = room.message_set.all()
    files = room.files.all() 
    can_upload = False
    
    if request.user.is_authenticated:
        if request.user.userprofile == room.host:
            can_upload = True

    if request.user.userprofile == room.host or room.is_private==False or request.user.userprofile in pa:
        if request.method == 'POST':
            body = request.POST.get('body')
            if body:
                message = Message.objects.create(
                    user = request.user.userprofile,
                    room = room,
                    body = body,
                    image = request.FILES.get('image'),
                )
                room.participants.add(request.user.userprofile)

            if 'file' in request.FILES: 
                uploaded_file = request.FILES['file']
                RoomFile.objects.create(
                    room=room,
                    uploaded_by=request.user.userprofile,
                    file=uploaded_file,
                )
            return redirect('room',pk=room.id)
        
        context = {'rooms':room,
                    'message':messages, 
                    'participants': pa,
                    'created_at': datetime.now(), 
                    'files': files,
                    'can_upload': can_upload,
                    'message_id': None}
        return render(request,'room.html',context)
    
    elif room.is_private and request.user.userprofile not in pa:
        if request.method == 'POST' and 'answer' in request.POST:
            user_answer = request.POST.get('answer', '').strip().lower()
            correct_answers = room.answer.lower().split(',')  
            if any(keyword.strip() in user_answer for keyword in correct_answers):
                room.participants.add(request.user.userprofile)
                return redirect('room', pk=room.id)
            else:
                return redirect('list_room')
            
        return render(request, 'room_question.html', {'room': room})
        
    return redirect('list_room')

@login_required(login_url='login')
def createRoom(request):
    if not is_coordinators(request.user):
        return redirect('error_404')
    
    form = RoomForm()
    faculties = Faculties.objects.all()

    if request.method == 'POST':
        topic_id = request.POST.get('faculty')
        topic = Faculties.objects.get(pk=topic_id)

        is_private_value = request.POST.get('is_private') == 'True'

        Room.objects.create(
            host=request.user.userprofile,
            topic=topic,
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            is_private=is_private_value, 
            question=request.POST.get('question'),
            answer=request.POST.get('answer'),
        )
        return redirect('list_room')

    context = {'form': form, 'faculties': faculties}
    return render(request, 'room_form.html', context) 

@login_required(login_url='login')
def updateRoom(request,pk):
    if not is_coordinators(request.user):
        return redirect('error_404')
    
    room = Room.objects.get(id= pk)
    form = RoomForm(instance=room)
    faculties = Faculties.objects.all()
    if request.user.userprofile != room.host:
        return HttpResponse('')
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        faculties, created = Faculties.objects.get_or_create(name = topic_name)
        room.name = request.POST.get('name')
        room.topic = faculties
        room.description = request.POST.get('description')
        room.password = request.POST.get('password')
        room.save()

        return redirect('list_room')

    context = {'form':form,'faculties':faculties,'room':room}
    return render(request,'room_form.html',context)

@login_required(login_url='login')
def deleteRoom(request,pk):
    if not is_coordinators(request.user):
        return redirect('error_404')

    room = Room.objects.get(id = pk)
    room.delete()
    return redirect('list_room')

@login_required
def delete_file(request, file_id):
    if not is_coordinators(request.user):
        return redirect('error_404')
    
    file = get_object_or_404(RoomFile, id=file_id)
    file.delete()
    return redirect('room', pk=file.room.id)

def list_room(request):
    if is_admins(request.user) or is_guests(request.user):
        return redirect('error_404')
    
    user_profile = get_object_or_404(UserProfile, user=request.user)
    is_coordinator = False
    
    if request.user.is_authenticated:
        roles = [role.name for role in user_profile.roles.all()]

        if "marketing coordinator" in roles:
            is_coordinator = True
    
    room = Room.objects.all()
    return render(request, 'list_room.html',{
        'room':room,
        'is_coordinator':is_coordinator,
        })


