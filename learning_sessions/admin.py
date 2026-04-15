from django.contrib import admin

from learning_sessions.models import Message
from learning_sessions.models import Session


class MessageInline(admin.TabularInline):
    """Inline admin for messages within a session."""

    model = Message
    extra = 0
    fields = ['sequence', 'role', 'content', 'timestamp']
    readonly_fields = ['timestamp']
    ordering = ['sequence']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Admin configuration for Session model."""

    list_display = ['id', 'learner', 'scenario', 'status', 'created_date']
    list_filter = ['status', 'scenario']
    search_fields = ['learner__email', 'scenario__name']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin configuration for Message model."""

    list_display = ['id', 'session', 'role', 'sequence', 'timestamp']
    list_filter = ['role', 'session__scenario']
    search_fields = ['content']
