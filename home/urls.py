from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home, name='home'),
    path('upload/', views.file_upload_view, name='file_upload'),
    path('contribution/update/<int:pk>/', views.update_contribution, name='update_contribution'),
    path('contribution/delete/<int:pk>/', views.delete_contribution, name='delete_contribution'),
    path('upload/success/', views.upload_success, name='success_url'),
    path('faculties/<int:faculty_id>/files/', views.faculty_files, name='faculty_files'),
    path('download/contributions/', views.download_selected_contributions, name='download_selected_contributions'),
    path('update_profile/', views.update_profile, name='update_profile'),
    path('contributions/<int:contribution_id>/', views.contributions_detail, name='contributions_detail'),
    path('my-contributions/', views.my_contributions, name='my_contributions'),

    path('update-faculties/<int:faculty_id>/', views.update_faculty, name='update_faculty'),
    path('remove-faculties/<int:faculty_id>/', views.remove_faculty, name='remove_faculty'),
    path('profile/', views.user_profile, name='profile'),

    path('academic-years/', views.list_academic_years, name='list_academic_years'),
    path('academic-years/create/', views.create_academic_year, name='create_academic_year'),
    path('academic-years/update/<int:year_id>/', views.update_academic_year, name='update_academic_year'),
    path('academic-years/remove/<int:year_id>/', views.remove_academic_year, name='remove_academic_year'),

    path('faculties/', views.list_faculties, name='list_faculties'),
    path('faculties/create/', views.create_faculty, name='create_faculty'),
    path('faculties/update/<int:faculty_id>/', views.update_faculty, name='update_faculty'),
    path('faculties/remove/<int:faculty_id>/', views.remove_faculty, name='remove_faculty'),

    path('ad/roles/create/', views.create_role, name='create_role'),
    path('ad/roles/', views.role_list, name='role_list'),
    path('ad/roles/<int:role_id>/', views.delete_role, name='delete_role'),

    path('ad/contributions/manage/', views.all_contributions_view, name='manage_contributions'),
    path('ad/contribution/approve/<int:contribution_id>/', views.approve_contribution, name='approve_contribution'),
    path('ad/contribution/public/<int:contribution_id>/', views.public_contribution, name='public_contribution'),
    path('ad/contribution/reject/<int:contribution_id>/', views.reject_contribution, name='reject_contribution'),

    path('ad/accounts/', views.account_list, name='account_list'),
    path('ad/account/create/', views.create_account, name='create_account'),
    path('ad/accounts/edit/<int:pk>/', views.account_update, name='account_edit'),
    path('ad/accounts/delete/<int:pk>/', views.account_delete, name='account_delete'),
    
    path('ad/statistical-analysis/', views.statistical_analysis, name='statistical_analysis'),

    path('terms_policies/', views.term_policy, name='term_policy'),
    path('error_404/', views.error_404, name='error_404'),


    
    path('room/<str:pk>/',views.room,name="room"),
    path('create-room/',views.createRoom, name ="create-room"),
    path('update-room/<slug:pk>/',views.updateRoom, name ="update-room"),
    path('delete-room/<slug:pk>/',views.deleteRoom, name ="delete-room"),
    path('list_room/',views.list_room, name ="list_room"),
    path('delete_file/<int:file_id>/', views.delete_file, name='delete_file'),
]