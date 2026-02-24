"""
LearnHub Views - MongoEngine version
"""

from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers  # ← DODAJ OVO
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
from .models import Course, Lesson, StudentProgress
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt

from pymongo import MongoClient
from django.core.cache import cache
import json

@require_http_methods(["GET"])
@login_required

# @cache_page je vraćen → svi korisnici dijele isti cache entry
@cache_page(60 * 60)
def get_course_progress(request, course_id):
    """
    DEMO: Cache Poisoning (CVE-2020-13254)

    Mitigacija (zakomentarisana):
    - manual per-user caching
    - user-specific cache key
    """

    try:

        # MITIGACIJA ZAKOMENTARISANA — PER USER CACHE

        # request.session.modified = True

        # cache_key = f'course_progress_{course_id}_user_{request.user.id}'
        # cached_data = cache.get(cache_key)
        #
        # if cached_data is not None:
        #     return JsonResponse(cached_data)

    
        course = Course.objects(id=ObjectId(course_id)).first()
        if not course:
            return JsonResponse({'error': 'Course not found'}, status=404)

        student = request.user

        progress = StudentProgress.objects(
            student_id=student.id,
            course_id=ObjectId(course_id)
        ).first()

        if not progress:
            progress = StudentProgress(
                student_id=student.id,
                course_id=ObjectId(course_id),
                completed_lessons=[],
                completion_percentage=0,
                last_updated=datetime.now()
            )
            progress.save()

        lessons = Lesson.objects(course_id=ObjectId(course_id)).order_by('order')

        lessons_data = []
        for lesson in lessons:
            lessons_data.append({
                'id': str(lesson.id),
                'title': lesson.title,
                'order': lesson.order,

                # ⚠️ USER-SPECIFIC DATA — ali cache nije user-specific
                'completed': lesson.id in progress.completed_lessons
            })

        response_data = {
            'student_id': student.id,
            'student_name': student.username,
            'course_id': str(course.id),
            'course_title': course.title,
            'completed_lessons': lessons_data,
            'completion_percentage': progress.completion_percentage,
            'total_lessons': len(lessons_data)
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
@login_required
def complete_lesson(request, lesson_id):
    """
    Markira lekciju kao završenu
    """
    
    try:
        # Dohvati lekciju
        lesson = Lesson.objects(id=ObjectId(lesson_id)).first()
        if not lesson:
            return JsonResponse({'error': 'Lesson not found'}, status=404)
        
        student = request.user
        
        # Dohvati ili kreiraj progress
        progress = StudentProgress.objects(
            student_id=student.id,
            course_id=lesson.course_id
        ).first()
        
        if not progress:
            progress = StudentProgress(
                student_id=student.id,
                course_id=lesson.course_id,
                completed_lessons=[],
                completion_percentage=0,
                last_updated=datetime.now()
            )
        
        # Dodaj lekciju u completed
        if lesson.id not in progress.completed_lessons:
            progress.completed_lessons.append(lesson.id)
            progress.last_updated = datetime.now()
            progress.update_completion()
        
        return JsonResponse({
            'status': 'success',
            'lesson_id': str(lesson.id),
            'lesson_title': lesson.title,
            'new_completion': progress.completion_percentage
        })
    
    except InvalidId:
        return JsonResponse({'error': 'Invalid lesson ID'}, status=400)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        'status': 'ok',
        'service': 'LearnHub API',
        'cache_enabled': True,
        'database': 'MongoDB via MongoEngine'
    })



@csrf_exempt
@require_http_methods(["POST"])
def test_login(request):
    """
    Test login endpoint za dobijanje session cookie
    """
    import json
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            if not request.session.session_key:
                request.session.create()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Login successful',
                'user_id': user.id,
                'username': user.username,
                'sessionid': request.session.session_key
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid credentials'
            }, status=401)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
def vulnerable_login(request):
    """
    DEMO (RANJIVO): NoSQL Injection kroz direktno prosleđivanje user input-a u MongoDB query.

    Primjer napada (bypass):
    POST /login
    {"username": {"$ne": null}, "password": {"$ne": null}}
    """

    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')

        # MITIGACIJE 

        # # 1) Strict type checking (sprječava operator injection)
        # if not isinstance(username, str) or not isinstance(password, str):
        #     return JsonResponse({
        #         'status': 'error',
        #         'message': 'Invalid input type'
        #     }, status=400)

        # # 2) Whitelist regex validacija (format sanitization)
        # import re
        # if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        #     return JsonResponse({
        #         'status': 'error',
        #         'message': 'Invalid username format'
        #     }, status=400)

        # # 3) Length limits
        # if len(password) < 6 or len(password) > 100:
        #     return JsonResponse({
        #         'status': 'error',
        #         'message': 'Invalid password length'
        #     }, status=400)

        # # 4) Defense-in-depth (konverzija u string)
        # username = str(username)
        # password = str(password)

       

        client = MongoClient('mongodb://localhost:27017/')
        db = client['learnhub_db']

        query = {
            'username': username,   
            'password': password   
        }

        print(f"[VULNERABLE] Executing MongoDB query: {query}")

        user = db.auth_users.find_one(query)

        if user:
            user['_id'] = str(user['_id'])
            return JsonResponse({
                'status': 'success',
                'message': f"Successfully logged in as {user.get('username')}",
                'user_id': user['_id']
            }, status=200)

        return JsonResponse({
            'status': 'error',
            'message': 'Invalid credentials'
        }, status=401)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON format'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Server error: {str(e)}'}, status=500)