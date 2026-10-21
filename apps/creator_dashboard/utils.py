from rest_framework.decorators import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response


class BaseAPIView(APIView):
    
    def success_response(self, message="Your request is Accepted", data = None, status_code = status.HTTP_200_OK):
        return Response({
            "success":True,
            "message":message,
            "data":data or [],
            "status":status_code
        }, status=status_code)
        
    def error_response(self, message="Your request is Rejected", data=None, status_code= status.HTTP_400_BAD_REQUEST):
        return Response({
            "success":False,
            "message":message,
            "data":data or [],
            "status":status_code
        }, status=status_code)
    

import base64
import hashlib
import hmac
import os
from django.conf import settings


def generate_code_verifier():
    return base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode()


def generate_code_verifier_from_state_id(state_id):
    digest = hmac.new(settings.SECRET_KEY.encode(), state_id.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()


def generate_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()