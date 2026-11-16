from django.urls import path

from . import views


app_name = 'pages'

urlpatterns = [
    path('', views.home, name='home'),
    path('opportunities/', views.opportunity_page, {'page_type': 'all'}, name='opportunities'),
    path('schemes/', views.opportunity_page, {'page_type': 'schemes'}, name='schemes'),
    path('scholarships/', views.opportunity_page, {'page_type': 'scholarships'}, name='scholarships'),
    path('internships/', views.opportunity_page, {'page_type': 'internships'}, name='internships'),
    path('opportunity/<str:opportunity_id>/', views.opportunity_detail, name='opportunity_detail'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),
]
