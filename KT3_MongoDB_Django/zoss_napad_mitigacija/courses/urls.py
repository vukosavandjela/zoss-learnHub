"""
URL Configuration za courses app
"""

from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # ⚠️ RANJIV ENDPOINT - promenjeno u <str:course_id>
    path('course/<str:course_id>/progress/', 
         views.get_course_progress, 
         name='course_progress'),
    
    # Helper endpoints
    path('lesson/<str:lesson_id>/complete/', 
         views.complete_lesson, 
         name='complete_lesson'),
    
    path('health/', 
         views.health_check, 
         name='health'),
    
    path('test-login/', 
         views.test_login, 
         name='test_login'),

    path('login-vulnerable/', 
         views.vulnerable_login, 
         name='vulnerable_login'),
    
   
  
]