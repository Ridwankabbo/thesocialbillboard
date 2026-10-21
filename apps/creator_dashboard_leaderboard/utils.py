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