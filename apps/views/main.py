from django.http import JsonResponse
from rest_framework.decorators import api_view


@api_view(['GET'])
def hello_world(request):
    d = {
        'message': 'Hello World'
    }
    return JsonResponse(d)
