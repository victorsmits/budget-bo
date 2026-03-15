from math import ceil
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class UniformPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "size"
    max_page_size = 200

    def get_paginated_response(self, data):
        return Response({
            "items": data,
            "total": self.page.paginator.count,
            "page": self.page.number,
            "pages": ceil(self.page.paginator.count / self.get_page_size(self.request)) if self.get_page_size(self.request) else 1,
            "size": self.get_page_size(self.request),
        })
