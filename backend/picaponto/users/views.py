import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import User


def user_data(user):
    return {
        'id': user.pk,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'employer_id': user.employer_id,
        'is_admin': user.is_staff or user.is_superuser,
    }


@ensure_csrf_cookie
@require_GET
def csrf(request):
    return JsonResponse({'message': 'CSRF cookie set.'})


@require_POST
def login_view(request):
    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'error': 'Expected a JSON object.'}, status=400)
    user = authenticate(request, username=data.get('username'), password=data.get('password'))
    if user is None:
        return JsonResponse({'error': 'Invalid credentials.'}, status=401)
    login(request, user)
    return JsonResponse({'user': user_data(user)})


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({'message': 'Logged out.'})


@require_GET
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)
    return JsonResponse({'user': user_data(request.user)})


@require_GET
def workers(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)
    if request.user.is_staff or request.user.is_superuser:
        queryset = User.objects.filter(role=User.Roles.WORKER)
    elif request.user.is_employer():
        queryset = request.user.workers.filter(role=User.Roles.WORKER)
    else:
        return JsonResponse({'error': 'Employer access required.'}, status=403)
    return JsonResponse({'workers': [user_data(user) for user in queryset.order_by('username')]})
