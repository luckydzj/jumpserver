# -*- coding: utf-8 -*-
#
from importlib import import_module

from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics

from common.drf.api import JMSReadOnlyModelViewSet
from common.plugins.es import QuerySet as ESQuerySet
from common.drf.filters import DatetimeRangeFilter
from common.api import CommonGenericViewSet
from orgs.mixins.api import OrgGenericViewSet, OrgBulkModelViewSet, OrgRelationMixin
from orgs.utils import current_org
from ops.models import CommandExecution
from . import filters
from .backends import TYPE_ENGINE_MAPPING
from .models import FTPLog, UserLoginLog, OperateLog, PasswordChangeLog
from .serializers import FTPLogSerializer, UserLoginLogSerializer, CommandExecutionSerializer
from .serializers import (
    OperateLogSerializer, OperateLogActionDetailSerializer,
    PasswordChangeLogSerializer, CommandExecutionHostsRelationSerializer
)


class FTPLogViewSet(CreateModelMixin,
                    ListModelMixin,
                    OrgGenericViewSet):
    model = FTPLog
    serializer_class = FTPLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'asset', 'system_user', 'filename']
    search_fields = filterset_fields
    ordering = ['-date_start']


class UserLoginCommonMixin:
    queryset = UserLoginLog.objects.all()
    serializer_class = UserLoginLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['username', 'ip', 'city', 'type', 'status', 'mfa']
    search_fields = ['username', 'ip', 'city']


class UserLoginLogViewSet(UserLoginCommonMixin, ListModelMixin, CommonGenericViewSet):

    @staticmethod
    def get_org_members():
        users = current_org.get_members().values_list('username', flat=True)
        return users

    def get_queryset(self):
        queryset = super().get_queryset()
        if current_org.is_root():
            return queryset
        users = self.get_org_members()
        queryset = queryset.filter(username__in=users)
        return queryset


class MyLoginLogAPIView(UserLoginCommonMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(username=self.request.user.username)
        return qs


class OperateLogViewSet(RetrieveModelMixin, ListModelMixin, OrgGenericViewSet):
    model = OperateLog
    serializer_class = OperateLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'action', 'resource_type', 'resource', 'remote_addr']
    search_fields = ['resource']
    ordering = ['-datetime']

    def get_serializer_class(self):
        if self.request.query_params.get('type') == 'action_detail':
            return OperateLogActionDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        qs = OperateLog.objects.all()
        es_config = settings.OPERATE_LOG_ELASTICSEARCH_CONFIG
        if es_config:
            engine_mod = import_module(TYPE_ENGINE_MAPPING['es'])
            store = engine_mod.OperateLogStore(es_config)
            if store.ping(timeout=2):
                qs = ESQuerySet(store)
                qs.model = OperateLog
        return qs


class PasswordChangeLogViewSet(ListModelMixin, CommonGenericViewSet):
    queryset = PasswordChangeLog.objects.all()
    serializer_class = PasswordChangeLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'change_by', 'remote_addr']
    search_fields = filterset_fields
    ordering = ['-datetime']

    def get_queryset(self):
        users = current_org.get_members()
        queryset = super().get_queryset().filter(
            user__in=[user.__str__() for user in users]
        )
        return queryset


class CommandExecutionViewSet(ListModelMixin, OrgGenericViewSet):
    model = CommandExecution
    serializer_class = CommandExecutionSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    filterset_fields = [
        'user__name', 'user__username', 'command',
        'run_as__name', 'run_as__username', 'is_finished'
    ]
    search_fields = [
        'command', 'user__name', 'user__username',
        'run_as__name', 'run_as__username',
    ]
    ordering = ['-date_created']

    def get_queryset(self):
        queryset = super().get_queryset()
        if current_org.is_root():
            return queryset
        queryset = queryset.filter(run_as__org_id=current_org.org_id())
        return queryset


class CommandExecutionHostRelationViewSet(OrgRelationMixin, OrgBulkModelViewSet):
    serializer_class = CommandExecutionHostsRelationSerializer
    m2m_field = CommandExecution.hosts.field
    filterset_class = filters.CommandExecutionFilter
    search_fields = ('asset__hostname', )
    http_method_names = ['options', 'get']
    rbac_perms = {
        'GET': 'ops.view_commandexecution',
        'list': 'ops.view_commandexecution',
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            asset_display=Concat(
                F('asset__hostname'), Value('('),
                F('asset__ip'), Value(')')
            )
        )
        return queryset
