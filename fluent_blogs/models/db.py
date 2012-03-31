from django.conf import settings
from django.contrib import comments
from django.contrib.auth.models import User
from django.contrib.contenttypes.generic import GenericRelation
from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import ugettext_lazy as _
from fluent_contents.models.fields import PlaceholderField
from fluent_blogs.urlresolvers import blog_reverse
from fluent_blogs.models.managers import EntryManager
from fluent_blogs import appsettings

# Optional tagging support
TaggableManager = None
if 'taggit_autocomplete_modified' in settings.INSTALLED_APPS:
    from taggit_autocomplete_modified.managers import TaggableManagerAutocomplete as TaggableManager
elif 'taggit' in settings.INSTALLED_APPS:
    from taggit.managers import TaggableManager


def _get_current_site():
    return Site.objects.get_current()



class Entry(models.Model):
    # Some publication states
    DRAFT = 'd'
    PUBLISHED = 'p'
    STATUSES = (
        (PUBLISHED, _('Published')),
        (DRAFT, _('Draft')),
    )

    title = models.CharField(_("Title"), max_length=200)
    slug = models.SlugField(_("Slug"))
    intro = models.TextField(_("Introtext"))
    contents = PlaceholderField("blog_contents")
    parent_site = models.ForeignKey(Site, editable=False, default=_get_current_site)

    status = models.CharField(_('status'), max_length=1, choices=STATUSES, default=DRAFT, db_index=True)
    publication_date = models.DateTimeField(_('publication date'), null=True, db_index=True, help_text=_('''When the page should go live, status must be "Published".'''))
    publication_end_date = models.DateTimeField(_('publication end date'), null=True, blank=True, db_index=True)

    # Metadata
    author = models.ForeignKey(User, verbose_name=_('author'), editable=False)
    creation_date = models.DateTimeField(_('creation date'), editable=False, auto_now_add=True)
    modification_date = models.DateTimeField(_('last modification'), editable=False, auto_now=True)

    objects = EntryManager()
    all_comments = GenericRelation(comments.get_model(), verbose_name=_("Comments"))
    categories = models.ManyToManyField(appsettings.FLUENT_BLOGS_CATEGORY_MODEL, verbose_name=_("Categories"), blank=True)

    if TaggableManager is not None:
        tags = TaggableManager(blank=True)
    else:
        tags = None


    class Meta:
        app_label = 'fluent_blogs'  # required for models subfolder
        verbose_name = _("Blog entry")
        verbose_name_plural = _("Blog entries")
        ordering = ('-publication_date',)


    def __unicode__(self):
        return self.title


    def get_absolute_url(self):
        root = blog_reverse('entry_archive_index', ignore_multiple=True)
        return root + self.get_app_url()


    def get_app_url(self):
        return appsettings.FLUENT_BLOGS_ENTRY_LINK_STYLE.lstrip('/').format(
            year = self.publication_date.strftime('%Y'),
            month = self.publication_date.strftime('%m'),
            day = self.publication_date.strftime('%d'),
            slug = self.slug,
            pk = self.pk,
        )


    def get_short_url(self):
        return blog_reverse('entry_shortlink', kwargs={'pk': self.id}, ignore_multiple=True)


    @property
    def url(self):
        """
        The URL of the page, provided for template code.
        """
        return self.get_absolute_url()


    @property
    def is_published(self):
        return self.status == self.PUBLISHED


    @property
    def is_draft(self):
        return self.status == self.DRAFT


    @property
    def comments(self):
        """Return the visible comments."""
        return comments.get_model().objects.for_model(self).filter(is_public=True)


    @property
    def comments_are_open(self):
        """Check if comments are open"""
        #if AUTO_CLOSE_COMMENTS_AFTER and self.comment_enabled:
        #    return (datetime.now() - self.start_publication).days <\
        #           AUTO_CLOSE_COMMENTS_AFTER
        #return self.comment_enabled
        return True


    @property
    def pingback_enabled(self):
        return False


    @property
    def previous_entry(self):
        """
        Return the previous entry
        """
        entries = self.__class__.objects.published().filter(publication_date__lt=self.publication_date).order_by('-publication_date')[:1]
        return entries[0] if entries else None


    @property
    def next_entry(self):
        """
        Return the next entry
        """
        entries = self.__class__.objects.published().filter(publication_date__gt=self.publication_date).order_by('publication_date')[:1]
        return entries[0] if entries else None