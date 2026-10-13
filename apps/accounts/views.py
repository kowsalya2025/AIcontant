from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout

from .models import Student, LearningProfile
from .serializers import (
    RegisterSerializer, LoginSerializer,
    StudentSerializer, LearningProfileSerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Register a new student account."""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        student = serializer.save()
        token, _ = Token.objects.get_or_create(user=student)
        return Response({
            'token': token.key,
            'user': StudentSerializer(student).data,
            'message': 'Account created successfully!'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Authenticate and return token."""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': StudentSerializer(user).data,
            'message': 'Login successful!'
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Revoke authentication token."""
    request.user.auth_token.delete()
    return Response({'message': 'Logged out successfully.'})


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Get or update student learning profile."""
    student = request.user
    if request.method == 'GET':
        profile_data = StudentSerializer(student).data
        try:
            lp = LearningProfileSerializer(student.learning_profile).data
        except LearningProfile.DoesNotExist:
            lp = {}
        return Response({'student': profile_data, 'learning_profile': lp})

    elif request.method == 'PUT':
        serializer = StudentSerializer(student, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'student': serializer.data,
                'message': 'Profile updated successfully!'
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats_view(request):
    """Return stats for the student dashboard."""
    student = request.user
    try:
        lp = student.learning_profile
        stats = {
            'display_name': student.display_name,
            'total_points': student.total_points,
            'current_streak': student.current_streak,
            'longest_streak': student.longest_streak,
            'skill_level': student.skill_level,
            'learning_style': student.learning_style,
            'preferred_subjects': student.preferred_subjects,
            'average_quiz_score': round(lp.average_quiz_score, 1),
            'total_content_generated': lp.total_content_generated,
            'total_quizzes_taken': lp.total_quizzes_taken,
            'completed_topics': lp.completed_topics,
            'weak_topics': lp.weak_topics,
            'strong_topics': lp.strong_topics,
        }
    except Exception:
        stats = {
            'display_name': student.display_name,
            'total_points': 0, 'current_streak': 0,
            'longest_streak': 0, 'skill_level': student.skill_level,
            'learning_style': student.learning_style,
        }
    return Response(stats)
