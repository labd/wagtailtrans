from django.core.management.base import BaseCommand
from wagtail.models import Page

from wagtailtrans.models import Language, TranslatablePageItem


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        default_language = Language.objects.default()
        pages = Page.objects.all().specific()

        for page in pages:
            if hasattr(page, 'create_translation') and not page.translatable_page_item:
                TranslatablePageItem.objects.create(
                    page=page,
                    language=default_language,
                )
