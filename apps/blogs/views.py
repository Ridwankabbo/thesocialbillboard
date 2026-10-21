from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import BlogPost
from .serializers import BlogPostSerializer


# Base API view providing standardized success/error response helpers
class BaseAPIView(APIView):
    # Return a normalized success payload with optional data and custom status
    def success_response(self, message="Request accepted", data=None, status_code=status.HTTP_200_OK):
        return Response({
            "success": True,
            "message": message,
            "status": status_code,
            "data": data or {}
        }, status=status_code)

    # Return a normalized error payload with optional details and custom status
    def error_response(self, message="Request rejected", data=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({
            "success": False,
            "message": message,
            "status": status_code,
            "data": data or {}
        }, status=status_code)


# Public endpoint: list all blog posts
class BlogListAPIView(BaseAPIView):
    # Fetch and serialize every BlogPost
    def get(self, request):
        blogs = BlogPost.objects.all()
        serializer = BlogPostSerializer(blogs, many=True)
        return self.success_response("All blog posts retrieved successfully.", serializer.data)


# Public endpoint: retrieve details of a single blog post by slug
class BlogDetailAPIView(BaseAPIView):
    # Find blog by slug (404 if missing) and serialize it
    def get(self, request, slug):
        blog = get_object_or_404(BlogPost, slug=slug)
        serializer = BlogPostSerializer(blog)
        return self.success_response("Blog post retrieved successfully.", serializer.data)


# Public endpoint: list the most recent 3 blog posts
class RecentBlogsAPIView(BaseAPIView):
    # Order by published_date descending and return top three
    def get(self, request):
        recent_blogs = BlogPost.objects.all().order_by('-published_date')[:3]
        serializer = BlogPostSerializer(recent_blogs, many=True)
        return self.success_response("Recent blog posts retrieved successfully.", serializer.data)
