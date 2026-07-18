
import django_filters

from core.models import Book, Genre


class BookFilter(django_filters.FilterSet):
    genre = django_filters.CharFilter(method="filter_genre")
    year_from = django_filters.NumberFilter(field_name="year", lookup_expr="gte")
    year_to = django_filters.NumberFilter(field_name="year", lookup_expr="lte")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Book
        fields: list[str] = []

    def filter_genre(self, queryset, name, value):
        return queryset.filter(genre__translations__name__iexact=value).distinct()

    def filter_search(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(translations__title__icontains=value)
            | Q(author__translations__name__icontains=value)
        ).distinct()
