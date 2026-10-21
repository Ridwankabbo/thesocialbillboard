from django.shortcuts import render
from rest_framework.decorators import APIView
from rest_framework.response import Response
from .serializers import NewsLetterSerializer
# Create your views here.

class NewsLetterAPIView(APIView):
    
    def post(self, request):
        serializer = NewsLetterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status":True,
                "message":"You have successfully subscribed to our newsletter"
            })
            
        return Response({
            "status":False,
            "message":"Subscription Failed"
        })

