import os
from functools import wraps

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import m2m_changed, post_save, pre_delete
from wagtail.admin.signals import init_new_page
from wagtail.models import Site, get_page_models

from wagtailtrans.conf import get_wagtailtrans_setting
from wagtailtrans.models import Language, SiteLanguages, TranslatablePage, TranslatablePageItem
from wagtailtrans.permissions import create_group_permissions, get_or_create_language_group


def disable_for_loaddata(signal_handler):
    """Decorator that turns off signal handlers when loading fixture data."""

    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        disable_signals = os.environ.get('WAGTAILTRANS_DISABLE_SIGNALS', False)
        if kwargs.get('raw') or bool(disable_signals):
            return
        signal_handler(*args, **kwargs)
    return wrapper


@disable_for_loaddata
def synchronize_trees(page, created=False):
    """Synchronize the translation trees when
    a TranslatablePageMixin is created.

    :param page: TranslatablePageMixin instance
    :param created: Page created True of False

    """
    try:
        site = page.get_site()
    except ObjectDoesNotExist:
        return

    # if get_wagtailtrans_setting('LANGUAGES_PER_SITE'):
    #     site_default = site.sitelanguages.default_language
    #     is_default_language = instance.language == site_default
    #     other_languages = site.sitelanguages.other_languages.all()

    language = page.language

    # Assign default language to new page
    if created and not language:
        language = Language.objects.default_for_site(site=site)
        TranslatablePageItem.objects.create(page=page, language=language)

    is_default_language = language.is_default if language else None
    other_languages = Language.objects.filter(is_default=False)

    # Page is not eligable for triggering creation of translations
    if not created or not language or not is_default_language:
        return

    # Create translations
    for lang in other_languages:
        page.create_translation(language=lang, copy_fields=True)


def create_new_language_tree_for_site(site, language):
    """Create a new language tree for a specific site.

    :param site: The site for which a new tree wil be created
    :param language: The language in which the tree wil be created
    """
    site_pages = site.root_page.get_children().values_list('pk', flat=True)
    default_language = (
        site.sitelanguages.default_language
        if get_wagtailtrans_setting('LANGUAGES_PER_SITE')
        else Language.objects.default()
    )
    canonical_home_page = TranslatablePageItem.objects.filter(page__pk__in=site_pages, language=default_language).first()
    if not canonical_home_page:
        # no pages created yet.
        return
    descendants = canonical_home_page.page.get_descendants(inclusive=True)
    for child_page in descendants:
        child_page = child_page.specific
        if hasattr(child_page, 'language') and not child_page.has_translation(language):
            child_page.create_translation(language, copy_fields=True)


def create_new_language_tree(sender, instance, **kwargs):
    """Signal will catch creation of a new language
    If sync trees is enabled it will create a whole new tree with
    correlating language.

    :param sender: Sender model
    :param instance: Language instance
    :param kwargs: kwargs e.g. created

    """
    if not kwargs.get('created'):
        return

    for site in Site.objects.all():
        create_new_language_tree_for_site(site, instance)


@disable_for_loaddata
def update_language_trees_for_site(sender, instance, action, pk_set, **kwargs):
    """Create a new language tree for a site if a new language is added to it..

    :param sender: Sender model
    :param instance: Language instance
    :param action: The type of change to the m2m field
    :param pk_set: Pks of the changed relations
    :param kwargs: kwargs e.g. created

    """
    if action == 'post_add':
        for language in Language.objects.filter(pk__in=pk_set):
            create_new_language_tree_for_site(instance.site, language)


@disable_for_loaddata
def create_language_permissions_and_group(sender, instance, **kwargs):
    """Create a new `Translator` role with it's required permissions.

    :param sender: Sender model
    :param instance: Language instance
    :param kwargs: kwargs e.g. created

    """
    if not kwargs.get('created'):
        return

    group = get_or_create_language_group(instance)
    create_group_permissions(group, instance)


def force_parent_language(sender, page, parent, **kwargs):
    """Force the initial language of the first page, before creating..

    When adding a homepage to a site, the initial language should be set.
    By default we set the default language from the Languages model, however
    when the languages are defined per site, it's possible that the default
    language differs from the database default.

    """
    #: Force the page language according to the parent, when the parent
    #: has no language set and is a site root page, force the default language
    #: For now we assume there isn't more than 1 site rooted at the parent.
    if hasattr(parent, 'language'):
        page.language = parent.language
    elif get_wagtailtrans_setting('LANGUAGES_PER_SITE'):
        site = parent.sites_rooted_here.first()
        if site:
            lang_settings = SiteLanguages.for_site(site)
            page.language = lang_settings.default_language or Language.objects.default()


def register_signal_handlers():
    """Registers signal handlers.

    To create a signal for TranslatablePage we have to use wagtails
    get_page_model.

    """
    # TODO: Make this optional via settings
    post_save.connect(create_language_permissions_and_group, sender=Language)
    # init_new_page.connect(force_parent_language)
    
    if get_wagtailtrans_setting('SYNC_TREE'):
        if get_wagtailtrans_setting('LANGUAGES_PER_SITE'):
            m2m_changed.connect(update_language_trees_for_site, sender=SiteLanguages.other_languages.through)
        else:
            post_save.connect(create_new_language_tree, sender=Language)
    
    pass

    # if get_wagtailtrans_setting('SYNC_TREE'):
    #     if get_wagtailtrans_setting('LANGUAGES_PER_SITE'):
    #         m2m_changed.connect(update_language_trees_for_site, sender=SiteLanguages.other_languages.through)
    #     else:
    #         post_save.connect(create_new_language_tree, sender=Language)
    #
    #     for model in get_page_models():
    #         if hasattr(model, 'create_translation'):
    #             post_save.connect(synchronize_trees, sender=model)
    #
    #         if hasattr(model, 'get_translations'):
    #             pre_delete.connect(synchronize_deletions, sender=model)
