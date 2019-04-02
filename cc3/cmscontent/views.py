from django.views.generic import DetailView, ListView

from .models import NewsEntry


class NewsEntryListView(ListView):
    model = NewsEntry
    paginate_by = 10
    template_name = 'cmscontent/news_page.html'


class NewsEntryDetailView(DetailView):
    model = NewsEntry
    template_name = 'cmscontent/news_detail.html'
