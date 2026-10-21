from django.shortcuts import render
from .models import CreatorProduct
from rest_framework import viewsets 
from .serializers import CreatorProductSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
class BaseAPIView(APIView):
    def success_response(self, message="Your request Accepted", data=None, status_code= status.HTTP_200_OK):
        return Response(
            {
            "success": True,
            "message": message,
            "status": status_code,
            "data": data or {}
            },
            status=status_code )
    def error_response(self, message="Your request rejected", data=None, status_code= status.HTTP_400_BAD_REQUEST):
        return Response(
            {
            "success": False,
            "message": message,
            "status": status_code,
            "data": data or {}
            },
            status=status_code )


class CreatorProductListView(BaseAPIView):
    def get(self, request):
        products = CreatorProduct.objects.all()
        serializer = CreatorProductSerializer(products, many=True)
        return self.success_response(
            message="Products fetched successfully",
            data=serializer.data
        )


class CreatorProductViewSet(BaseAPIView, viewsets.ModelViewSet):
    queryset = CreatorProduct.objects.all()
    serializer_class = CreatorProductSerializer
