"""
LearnHub Models - MongoEngine version
"""

from mongoengine import Document, fields
from django.contrib.auth.models import User


class Course(Document):
    """
    Kurs koji instruktor kreira
    """
    title = fields.StringField(max_length=200, required=True)
    description = fields.StringField()
    instructor_id = fields.IntField(required=True)  # Django User ID
    created_at = fields.DateTimeField()
    
    meta = {
        'collection': 'courses',
        'db_alias': 'default'
    }
    
    def __str__(self):
        return self.title


class Lesson(Document):
    """
    Lekcija unutar kursa
    """
    course_id = fields.ObjectIdField(required=True)  # Reference to Course
    title = fields.StringField(max_length=200, required=True)
    content = fields.StringField()
    order = fields.IntField(default=0)
    
    meta = {
        'collection': 'lessons',
        'ordering': ['order'],
        'db_alias': 'default'
    }
    
    def __str__(self):
        return self.title


class StudentProgress(Document):
    """
    ⚠️ KLJUČNI MODEL ZA CACHE POISONING NAPAD
    """
    student_id = fields.IntField(required=True)  # Django User ID
    course_id = fields.ObjectIdField(required=True)  # Reference to Course
    completed_lessons = fields.ListField(fields.ObjectIdField(), default=list)
    completion_percentage = fields.IntField(default=0)
    last_updated = fields.DateTimeField()
    
    meta = {
        'collection': 'student_progress',
        'db_alias': 'default',
        'indexes': [
            {'fields': ['student_id', 'course_id'], 'unique': True}
        ]
    }
    
    def __str__(self):
        return f"Student {self.student_id} - Course {self.course_id}"
    
    def update_completion(self):
        """Računa procenat završenosti"""
        from bson import ObjectId
        total_lessons = Lesson.objects(course_id=ObjectId(self.course_id)).count()
        if total_lessons > 0:
            completed_count = len(self.completed_lessons)
            self.completion_percentage = int((completed_count / total_lessons) * 100)
        else:
            self.completion_percentage = 0
        self.save()