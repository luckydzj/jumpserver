import uuid

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext, ugettext_lazy as _
from django.utils import timezone

from common.utils import lazyproperty
from common.db.encoder import ModelJSONFieldEncoder
from orgs.mixins.models import OrgModelMixin, Organization
from orgs.utils import current_org

__all__ = [
    'FTPLog', 'OperateLog', 'PasswordChangeLog', 'UserLoginLog',
]


class FTPLog(OrgModelMixin):
    OPERATE_DELETE = 'Delete'
    OPERATE_UPLOAD = 'Upload'
    OPERATE_DOWNLOAD = 'Download'
    OPERATE_RMDIR = 'Rmdir'
    OPERATE_RENAME = 'Rename'
    OPERATE_MKDIR = 'Mkdir'
    OPERATE_SYMLINK = 'Symlink'

    OPERATE_CHOICES = (
        (OPERATE_DELETE, _('Delete')),
        (OPERATE_UPLOAD, _('Upload')),
        (OPERATE_DOWNLOAD, _('Download')),
        (OPERATE_RMDIR, _('Rmdir')),
        (OPERATE_RENAME, _('Rename')),
        (OPERATE_MKDIR, _('Mkdir')),
        (OPERATE_SYMLINK, _('Symlink'))
    )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_('User'))
    remote_addr = models.CharField(max_length=128, verbose_name=_("Remote addr"), blank=True, null=True)
    asset = models.CharField(max_length=1024, verbose_name=_("Asset"))
    system_user = models.CharField(max_length=128, verbose_name=_("System user"))
    operate = models.CharField(max_length=16, verbose_name=_("Operate"), choices=OPERATE_CHOICES)
    filename = models.CharField(max_length=1024, verbose_name=_("Filename"))
    is_success = models.BooleanField(default=True, verbose_name=_("Success"))
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Date start'))

    class Meta:
        verbose_name = _("File transfer log")


class OperateLog(OrgModelMixin):
    ACTION_CREATE = 'create'
    ACTION_VIEW = 'view'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_CHOICES = (
        (ACTION_CREATE, _("Create")),
        (ACTION_VIEW, _("View")),
        (ACTION_UPDATE, _("Update")),
        (ACTION_DELETE, _("Delete"))
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_('User'))
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, verbose_name=_("Action"))
    resource_type = models.CharField(max_length=64, verbose_name=_("Resource Type"))
    resource = models.CharField(max_length=128, verbose_name=_("Resource"))
    remote_addr = models.CharField(max_length=128, verbose_name=_("Remote addr"), blank=True, null=True)
    datetime = models.DateTimeField(auto_now=True, verbose_name=_('Datetime'), db_index=True)
    before = models.JSONField(default=dict, encoder=ModelJSONFieldEncoder, null=True)
    after = models.JSONField(default=dict, encoder=ModelJSONFieldEncoder, null=True)

    def __str__(self):
        return "<{}> {} <{}>".format(self.user, self.action, self.resource)

    @lazyproperty
    def resource_type_display(self):
        return gettext(self.resource_type)

    def save(self, *args, **kwargs):
        if current_org.is_root() and not self.org_id:
            self.org_id = Organization.ROOT_ID
        return super(OperateLog, self).save(*args, **kwargs)

    @classmethod
    def from_dict(cls, d):
        self = cls()
        for k, v in d.items():
            setattr(self, k, v)
        return self

    @classmethod
    def from_multi_dict(cls, l):
        operate_logs = []
        for d in l:
            operate_log = cls.from_dict(d)
            operate_logs.append(operate_log)
        return operate_logs

    class Meta:
        verbose_name = _("Operate log")


class PasswordChangeLog(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    user = models.CharField(max_length=128, verbose_name=_('User'))
    change_by = models.CharField(max_length=128, verbose_name=_("Change by"))
    remote_addr = models.CharField(max_length=128, verbose_name=_("Remote addr"), blank=True, null=True)
    datetime = models.DateTimeField(auto_now=True, verbose_name=_('Datetime'))

    def __str__(self):
        return "{} change {}'s password".format(self.change_by, self.user)

    class Meta:
        verbose_name = _('Password change log')


class UserLoginLog(models.Model):
    LOGIN_TYPE_CHOICE = (
        ('W', 'Web'),
        ('T', 'Terminal'),
        ('U', 'Unknown'),
    )

    MFA_DISABLED = 0
    MFA_ENABLED = 1
    MFA_UNKNOWN = 2

    MFA_CHOICE = (
        (MFA_DISABLED, _('Disabled')),
        (MFA_ENABLED, _('Enabled')),
        (MFA_UNKNOWN, _('-')),
    )

    STATUS_CHOICE = (
        (True, _('Success')),
        (False, _('Failed'))
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    username = models.CharField(max_length=128, verbose_name=_('Username'))
    type = models.CharField(choices=LOGIN_TYPE_CHOICE, max_length=2, verbose_name=_('Login type'))
    ip = models.GenericIPAddressField(verbose_name=_('Login ip'))
    city = models.CharField(max_length=254, blank=True, null=True, verbose_name=_('Login city'))
    user_agent = models.CharField(max_length=254, blank=True, null=True, verbose_name=_('User agent'))
    mfa = models.SmallIntegerField(default=MFA_UNKNOWN, choices=MFA_CHOICE, verbose_name=_('MFA'))
    reason = models.CharField(default='', max_length=128, blank=True, verbose_name=_('Reason'))
    status = models.BooleanField(max_length=2, default=True, choices=STATUS_CHOICE, verbose_name=_('Status'))
    datetime = models.DateTimeField(default=timezone.now, verbose_name=_('Date login'))
    backend = models.CharField(max_length=32, default='', verbose_name=_('Authentication backend'))

    @property
    def backend_display(self):
        return gettext(self.backend)

    @classmethod
    def get_login_logs(cls, date_from=None, date_to=None, user=None, keyword=None):
        login_logs = cls.objects.all()
        if date_from and date_to:
            date_from = "{} {}".format(date_from, '00:00:00')
            date_to = "{} {}".format(date_to, '23:59:59')
            login_logs = login_logs.filter(
                datetime__gte=date_from, datetime__lte=date_to
            )
        if user:
            login_logs = login_logs.filter(username=user)
        if keyword:
            login_logs = login_logs.filter(
                Q(ip__contains=keyword) |
                Q(city__contains=keyword) |
                Q(username__contains=keyword)
            )
        if not current_org.is_root():
            username_list = current_org.get_members().values_list('username', flat=True)
            login_logs = login_logs.filter(username__in=username_list)
        return login_logs

    @property
    def reason_display(self):
        from authentication.errors import reason_choices, old_reason_choices
        reason = reason_choices.get(self.reason)
        if reason:
            return reason
        reason = old_reason_choices.get(self.reason, self.reason)
        return reason

    class Meta:
        ordering = ['-datetime', 'username']
        verbose_name = _('User login log')
