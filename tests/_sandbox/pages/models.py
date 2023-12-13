from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page

from wagtailtrans.models import TranslatablePage, TranslatablePageMixin


class HomePage(TranslatablePageMixin, TranslatablePage):
    """An implementation of TranslatablePage."""

    subtitle = models.CharField(max_length=255, help_text="A required field, for test purposes")
    body = RichTextField(blank=True, default='')
    image = models.ForeignKey(
        'wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    content_panels = Page.content_panels + [
        FieldPanel('subtitle'),
        FieldPanel('body'),
        FieldPanel('image')
    ]

    subpage_types = ['HomePage']
