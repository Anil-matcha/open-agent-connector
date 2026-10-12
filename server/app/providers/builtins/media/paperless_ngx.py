"""
Paperless-ngx Provider for ConnectorHub.
Loads and registers 139 actions with exact route definitions and parameters.
"""
import base64
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://{{host}}"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "botToken"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["domain", "subdomain", "site", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
    return base

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = _extract_token(cred)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    auth_mode = "token_auth"
    if auth_mode == "Bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "token_auth":
        if token:
            headers["Authorization"] = f"Token {token}"
    elif auth_mode == "unsplash_client_id":
        if token:
            headers["Authorization"] = f"Client-ID {token}"
    elif auth_mode == "amplitude_basic":
        if token:
            secret = str(cred.get("secretKey") or cred.get("apiKeyId") or "X").strip()
            pair = f"{token}:{secret}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "x_api_key":
        if token:
            headers["X-API-Key"] = token
            headers["X-Api-Key"] = token

    return headers

ROUTES: Dict[str, List[Any]] = {
    "acknowledge_tasks": [
        "POST",
        "/api/tasks/acknowledge/",
        [],
        [
            "tasks",
            "all"
        ]
    ],
    "add_document_note": [
        "POST",
        "/api/documents/{documentId}/versions/{versionId}/",
        [
            "documentId",
            "versionId"
        ],
        [
            "id",
            "note"
        ]
    ],
    "autocomplete_search": [
        "GET",
        "/api/search/autocomplete/",
        [],
        [
            "term",
            "limit"
        ]
    ],
    "bulk_delete_processed_mail": [
        "POST",
        "/api/processed_mail/bulk_delete/",
        [],
        [
            "mail_ids"
        ]
    ],
    "bulk_download_documents": [
        "POST",
        "/api/documents/bulk_download/",
        [],
        [
            "documents",
            "all",
            "filters",
            "content",
            "compression",
            "follow_formatting"
        ]
    ],
    "bulk_edit_documents": [
        "PATCH",
        "/bulk_edit_documents",
        [],
        [
            "documents",
            "all",
            "filters",
            "method",
            "parameters"
        ]
    ],
    "bulk_edit_objects": [
        "POST",
        "/api/bulk_edit_objects/",
        [],
        [
            "object_type",
            "operation",
            "objects",
            "all",
            "filters",
            "owner",
            "permissions",
            "merge"
        ]
    ],
    "chat_with_documents": [
        "POST",
        "/api/documents/chat/",
        [],
        [
            "q",
            "document_id"
        ]
    ],
    "create_correspondent": [
        "POST",
        "/correspondent",
        [],
        [
            "name",
            "match",
            "matching_algorithm",
            "is_insensitive",
            "owner",
            "set_permissions"
        ]
    ],
    "create_custom_field": [
        "POST",
        "/custom_field",
        [],
        [
            "name",
            "data_type",
            "extra_data"
        ]
    ],
    "create_document_type": [
        "POST",
        "/document_type",
        [],
        [
            "name",
            "match",
            "matching_algorithm",
            "is_insensitive",
            "owner",
            "set_permissions"
        ]
    ],
    "create_group": [
        "POST",
        "/api/groups/",
        [],
        [
            "name",
            "permissions"
        ]
    ],
    "create_mail_account": [
        "POST",
        "/api/mail_accounts/",
        [],
        [
            "name",
            "imap_server",
            "imap_port",
            "imap_security",
            "username",
            "password",
            "character_set",
            "is_token",
            "account_type",
            "expiration",
            "owner",
            "set_permissions"
        ]
    ],
    "create_mail_rule": [
        "POST",
        "/api/mail_rules/",
        [],
        [
            "name",
            "account",
            "folder",
            "filter_from",
            "filter_to",
            "filter_subject",
            "filter_body",
            "filter_attachment_filename_include",
            "filter_attachment_filename_exclude",
            "maximum_age",
            "action",
            "action_parameter",
            "assign_title_from",
            "assign_tags",
            "assign_correspondent_from",
            "assign_correspondent",
            "assign_document_type",
            "assign_owner_from_rule",
            "order",
            "attachment_type",
            "consumption_scope",
            "pdf_layout",
            "enabled",
            "stop_processing",
            "owner",
            "set_permissions"
        ]
    ],
    "create_saved_view": [
        "POST",
        "/saved_view",
        [],
        [
            "name",
            "icon",
            "sort_field",
            "sort_reverse",
            "filter_rules",
            "page_size",
            "display_mode",
            "display_fields",
            "owner",
            "set_permissions"
        ]
    ],
    "create_share_link": [
        "POST",
        "{shareLinkBundlesPath}{id}/rebuild/",
        [
            "shareLinkBundlesPath",
            "id"
        ],
        [
            "document",
            "file_version",
            "expiration"
        ]
    ],
    "create_share_link_bundle": [
        "POST",
        "{shareLinkBundlesPath}{id}/rebuild/",
        [
            "shareLinkBundlesPath",
            "id"
        ],
        [
            "document_ids",
            "file_version",
            "expiration_days"
        ]
    ],
    "create_storage_path": [
        "POST",
        "/storage_path",
        [],
        [
            "name",
            "path",
            "match",
            "matching_algorithm",
            "is_insensitive",
            "owner",
            "set_permissions"
        ]
    ],
    "create_tag": [
        "POST",
        "/tag",
        [],
        [
            "name",
            "color",
            "match",
            "matching_algorithm",
            "is_insensitive",
            "is_inbox_tag",
            "parent",
            "owner",
            "set_permissions"
        ]
    ],
    "create_user": [
        "POST",
        "/api/users/",
        [],
        [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
            "is_superuser",
            "groups",
            "user_permissions"
        ]
    ],
    "create_workflow": [
        "POST",
        "/workflow",
        [],
        [
            "name",
            "order",
            "enabled",
            "triggers",
            "actions"
        ]
    ],
    "create_workflow_action": [
        "POST",
        "/workflow_action",
        [],
        [
            "type",
            "assign_title",
            "assign_tags",
            "assign_correspondent",
            "assign_document_type",
            "assign_storage_path",
            "assign_owner",
            "assign_view_users",
            "assign_view_groups",
            "assign_change_users",
            "assign_change_groups",
            "assign_custom_fields",
            "assign_custom_fields_values",
            "remove_all_tags",
            "remove_tags",
            "remove_all_correspondents",
            "remove_correspondents",
            "remove_all_document_types",
            "remove_document_types",
            "remove_all_storage_paths",
            "remove_storage_paths",
            "remove_custom_fields",
            "remove_all_custom_fields",
            "remove_all_owners",
            "remove_owners",
            "remove_all_permissions",
            "remove_view_users",
            "remove_view_groups",
            "remove_change_users",
            "remove_change_groups",
            "email",
            "webhook",
            "passwords",
            "ai_suggestion_fields",
            "ai_create_missing",
            "ai_overwrite_existing"
        ]
    ],
    "create_workflow_trigger": [
        "POST",
        "/workflow_trigger",
        [],
        [
            "type",
            "sources",
            "filter_path",
            "filter_filename",
            "filter_mailrule",
            "matching_algorithm",
            "match",
            "is_insensitive",
            "filter_has_tags",
            "filter_has_all_tags",
            "filter_has_not_tags",
            "filter_custom_field_query",
            "filter_has_any_correspondents",
            "filter_has_not_correspondents",
            "filter_has_any_document_types",
            "filter_has_not_document_types",
            "filter_has_any_storage_paths",
            "filter_has_not_storage_paths",
            "filter_has_correspondent",
            "filter_has_document_type",
            "filter_has_storage_path",
            "schedule_offset_days",
            "schedule_is_recurring",
            "schedule_recurring_interval_days",
            "schedule_date_field",
            "schedule_date_custom_field"
        ]
    ],
    "deactivate_user_totp": [
        "POST",
        "/api/users/{id}/deactivate_totp/",
        [
            "id"
        ],
        []
    ],
    "delete_correspondent": [
        "DELETE",
        "/correspondent",
        [],
        [
            "id"
        ]
    ],
    "delete_custom_field": [
        "DELETE",
        "/custom_field",
        [],
        [
            "id"
        ]
    ],
    "delete_document": [
        "DELETE",
        "/api/documents/{documentId}/",
        [
            "documentId"
        ],
        [
            "id"
        ]
    ],
    "delete_document_note": [
        "DELETE",
        "/api/documents/{documentId}/versions/{versionId}/",
        [
            "documentId",
            "versionId"
        ],
        [
            "id",
            "note_id"
        ]
    ],
    "delete_document_type": [
        "DELETE",
        "/document_type",
        [],
        [
            "id"
        ]
    ],
    "delete_document_version": [
        "DELETE",
        "/api/documents/{documentId}/versions/{versionId}/",
        [
            "documentId",
            "versionId"
        ],
        [
            "id",
            "version_id"
        ]
    ],
    "delete_documents": [
        "DELETE",
        "/documents",
        [],
        [
            "documents",
            "all",
            "filters"
        ]
    ],
    "delete_group": [
        "DELETE",
        "/api/groups/{id}/",
        [
            "id"
        ],
        []
    ],
    "delete_mail_account": [
        "DELETE",
        "/api/mail_accounts/{id}/",
        [
            "id"
        ],
        []
    ],
    "delete_mail_rule": [
        "DELETE",
        "/api/mail_rules/{id}/",
        [
            "id"
        ],
        []
    ],
    "delete_saved_view": [
        "DELETE",
        "/saved_view",
        [],
        [
            "id"
        ]
    ],
    "delete_share_link": [
        "DELETE",
        "/share_link",
        [],
        [
            "id"
        ]
    ],
    "delete_share_link_bundle": [
        "DELETE",
        "/share_link_bundle",
        [],
        [
            "id"
        ]
    ],
    "delete_storage_path": [
        "DELETE",
        "/storage_path",
        [],
        [
            "id"
        ]
    ],
    "delete_tag": [
        "DELETE",
        "/tag",
        [],
        [
            "id"
        ]
    ],
    "delete_user": [
        "DELETE",
        "/api/users/{id}/",
        [
            "id"
        ],
        []
    ],
    "delete_workflow": [
        "DELETE",
        "/workflow",
        [],
        [
            "id"
        ]
    ],
    "delete_workflow_action": [
        "DELETE",
        "/workflow_action",
        [],
        [
            "id"
        ]
    ],
    "delete_workflow_trigger": [
        "POST",
        "/workflow_trigger",
        [],
        [
            "id"
        ]
    ],
    "download_document": [
        "POST",
        "/api/documents/{documentId}/download/",
        [
            "documentId"
        ],
        [
            "id",
            "original",
            "version",
            "follow_formatting"
        ]
    ],
    "edit_document_pdf": [
        "POST",
        "/api/documents/bulk_download/",
        [],
        [
            "documents",
            "operations",
            "update_document",
            "include_metadata",
            "delete_original",
            "source_mode"
        ]
    ],
    "email_document": [
        "DELETE",
        "/api/documents/{documentId}/versions/{versionId}/",
        [
            "documentId",
            "versionId"
        ],
        [
            "id",
            "addresses",
            "subject",
            "message",
            "use_archive_version"
        ]
    ],
    "email_documents": [
        "DELETE",
        "/api/documents/{documentId}/versions/{versionId}/",
        [
            "documentId",
            "versionId"
        ],
        [
            "documents",
            "addresses",
            "subject",
            "message",
            "use_archive_version"
        ]
    ],
    "empty_trash": [
        "POST",
        "/api/documents/chat/",
        [],
        [
            "documents"
        ]
    ],
    "get_application_config": [
        "PATCH",
        "/api/config/{configId}/",
        [
            "configId"
        ],
        []
    ],
    "get_correspondent": [
        "GET",
        "/correspondent",
        [],
        [
            "id",
            "full_perms"
        ]
    ],
    "get_custom_field": [
        "GET",
        "/custom_field",
        [],
        [
            "id"
        ]
    ],
    "get_document": [
        "PATCH",
        "/api/documents/{documentId}/",
        [
            "documentId"
        ],
        [
            "id",
            "full_perms",
            "fields",
            "version"
        ]
    ],
    "get_document_ai_suggestions": [
        "POST",
        "/api/documents/{documentId}/download/",
        [
            "documentId"
        ],
        [
            "id"
        ]
    ],
    "get_document_history": [
        "DELETE",
        "/api/documents/{documentId}/versions/{versionId}/",
        [
            "documentId",
            "versionId"
        ],
        [
            "id"
        ]
    ],
    "get_document_metadata": [
        "GET",
        "/api/documents/{documentId}/download/",
        [
            "documentId"
        ],
        [
            "id",
            "version"
        ]
    ],
    "get_document_root": [
        "GET",
        "/api/documents/{documentId}/download/",
        [
            "documentId"
        ],
        [
            "id"
        ]
    ],
    "get_document_suggestions": [
        "POST",
        "/api/documents/{documentId}/download/",
        [
            "documentId"
        ],
        [
            "id"
        ]
    ],
    "get_document_thumbnail": [
        "POST",
        "/api/documents/{documentId}/thumb/",
        [
            "documentId"
        ],
        [
            "id",
            "version"
        ]
    ],
    "get_document_type": [
        "GET",
        "/document_type",
        [],
        [
            "id",
            "full_perms"
        ]
    ],
    "get_group": [
        "POST",
        "/api/groups/{id}/",
        [
            "id"
        ],
        []
    ],
    "get_log": [
        "GET",
        "/api/logs/{encodeURIComponent}/",
        [
            "encodeURIComponent"
        ],
        [
            "name",
            "limit"
        ]
    ],
    "get_mail_account": [
        "POST",
        "/api/mail_accounts/",
        [],
        [
            "id",
            "full_perms"
        ]
    ],
    "get_mail_rule": [
        "POST",
        "/api/mail_rules/",
        [],
        [
            "id",
            "full_perms"
        ]
    ],
    "get_next_asn": [
        "GET",
        "/api/documents/next_asn/",
        [],
        []
    ],
    "get_processed_mail": [
        "POST",
        "/api/processed_mail/{id}/",
        [
            "id"
        ],
        []
    ],
    "get_profile": [
        "PATCH",
        "/api/profile/",
        [],
        []
    ],
    "get_remote_version": [
        "POST",
        "/api/remote_version/",
        [],
        []
    ],
    "get_saved_view": [
        "GET",
        "/saved_view",
        [],
        [
            "id",
            "full_perms"
        ]
    ],
    "get_selection_data": [
        "POST",
        "/api/trash/",
        [],
        [
            "documents"
        ]
    ],
    "get_share_link": [
        "GET",
        "/share_link",
        [],
        [
            "id"
        ]
    ],
    "get_share_link_bundle": [
        "GET",
        "/share_link_bundle",
        [],
        [
            "id"
        ]
    ],
    "get_statistics": [
        "POST",
        "/api/statistics/",
        [],
        []
    ],
    "get_storage_path": [
        "GET",
        "/storage_path",
        [],
        [
            "id",
            "full_perms"
        ]
    ],
    "get_system_status": [
        "POST",
        "/api/status/",
        [],
        []
    ],
    "get_tag": [
        "GET",
        "/tag",
        [],
        [
            "id",
            "full_perms"
        ]
    ],
    "get_task": [
        "POST",
        "/api/tasks/",
        [],
        [
            "task_id"
        ]
    ],
    "get_task_by_id": [
        "POST",
        "/api/tasks/{id}/",
        [
            "id"
        ],
        []
    ],
    "get_task_status_counts": [
        "POST",
        "/api/tasks/status_counts/",
        [],
        [
            "task_id",
            "name",
            "result",
            "task_type",
            "trigger_source",
            "acknowledged",
            "owner",
            "date_created_after",
            "date_created_before",
            "additional_filters"
        ]
    ],
    "get_task_summary": [
        "POST",
        "/api/tasks/summary/",
        [],
        [
            "days"
        ]
    ],
    "get_ui_settings": [
        "POST",
        "/api/ui_settings/",
        [],
        []
    ],
    "get_user": [
        "POST",
        "/api/users/{id}/",
        [
            "id"
        ],
        []
    ],
    "get_workflow": [
        "GET",
        "/workflow",
        [],
        [
            "id"
        ]
    ],
    "get_workflow_action": [
        "GET",
        "/workflow_action",
        [],
        [
            "id"
        ]
    ],
    "get_workflow_trigger": [
        "POST",
        "/workflow_trigger",
        [],
        [
            "id"
        ]
    ],
    "global_search": [
        "GET",
        "/api/search/",
        [],
        [
            "query",
            "db_only"
        ]
    ],
    "list_active_tasks": [
        "POST",
        "/api/tasks/active/",
        [],
        []
    ],
    "list_correspondents": [
        "GET",
        "/correspondents",
        [],
        [
            "id",
            "id__in",
            "name__icontains",
            "name__iexact",
            "name__istartswith",
            "name__iendswith",
            "last_correspondence",
            "full_perms",
            "page",
            "page_size",
            "ordering",
            "additional_filters"
        ]
    ],
    "list_custom_fields": [
        "GET",
        "/custom_fields",
        [],
        [
            "id",
            "id__in",
            "name__icontains",
            "name__iexact",
            "name__istartswith",
            "name__iendswith",
            "page",
            "page_size",
            "ordering",
            "additional_filters"
        ]
    ],
    "list_document_notes": [
        "POST",
        "/api/documents/{documentId}/update_version/",
        [
            "documentId"
        ],
        [
            "id"
        ]
    ],
    "list_document_share_links": [
        "DELETE",
        "/api/documents/{documentId}/versions/{versionId}/",
        [
            "documentId",
            "versionId"
        ],
        [
            "id"
        ]
    ],
    "list_document_types": [
        "GET",
        "/document_types",
        [],
        [
            "id",
            "id__in",
            "name__icontains",
            "name__iexact",
            "name__istartswith",
            "name__iendswith",
            "full_perms",
            "page",
            "page_size",
            "ordering",
            "additional_filters"
        ]
    ],
    "list_documents": [
        "PATCH",
        "/api/documents/",
        [],
        [
            "page",
            "page_size",
            "ordering",
            "truncate_content",
            "fields",
            "full_perms",
            "include_selection_data",
            "query",
            "text",
            "title_search",
            "more_like_id",
            "id",
            "id__in",
            "title__istartswith",
            "title__iendswith",
            "title__icontains",
            "title__iexact",
            "archive_serial_number",
            "archive_serial_number__gt",
            "archive_serial_number__gte",
            "archive_serial_number__lt",
            "archive_serial_number__lte",
            "archive_serial_number__isnull",
            "created__year",
            "created__month",
            "created__day",
            "created__gt",
            "created__gte",
            "created__lt",
            "created__lte",
            "created__date__gt",
            "created__date__gte",
            "created__date__lt",
            "created__date__lte",
            "added__year",
            "added__month",
            "added__day",
            "added__date__gt",
            "added__date__gte",
            "added__date__lt",
            "added__date__lte",
            "added__gt",
            "added__gte",
            "added__lt",
            "added__lte",
            "modified__year",
            "modified__month",
            "modified__day",
            "modified__date__gt",
            "modified__date__gte",
            "modified__date__lt",
            "modified__date__lte",
            "modified__gt",
            "modified__gte",
            "modified__lt",
            "modified__lte",
            "original_filename__istartswith",
            "original_filename__iendswith",
            "original_filename__icontains",
            "original_filename__iexact",
            "checksum__istartswith",
            "checksum__iendswith",
            "checksum__icontains",
            "checksum__iexact",
            "correspondent__isnull",
            "correspondent__id",
            "correspondent__id__in",
            "correspondent__id__none",
            "correspondent__name__istartswith",
            "correspondent__name__iendswith",
            "correspondent__name__icontains",
            "correspondent__name__iexact",
            "tags__id",
            "tags__id__in",
            "tags__id__all",
            "tags__id__none",
            "tags__name__istartswith",
            "tags__name__iendswith",
            "tags__name__icontains",
            "tags__name__iexact",
            "document_type__isnull",
            "document_type__id",
            "document_type__id__in",
            "document_type__id__none",
            "document_type__name__istartswith",
            "document_type__name__iendswith",
            "document_type__name__icontains",
            "document_type__name__iexact",
            "storage_path__isnull",
            "storage_path__id",
            "storage_path__id__in",
            "storage_path__id__none",
            "storage_path__name__istartswith",
            "storage_path__name__iendswith",
            "storage_path__name__icontains",
            "storage_path__name__iexact",
            "owner__isnull",
            "owner__id",
            "owner__id__in",
            "owner__id__none",
            "is_tagged",
            "is_in_inbox",
            "title_content",
            "content__istartswith",
            "content__iendswith",
            "content__icontains",
            "content__iexact",
            "custom_fields__icontains",
            "custom_fields__id__all",
            "custom_fields__id__none",
            "custom_fields__id__in",
            "has_custom_fields",
            "custom_field_query",
            "shared_by__id",
            "mime_type",
            "additional_filters"
        ]
    ],
    "list_groups": [
        "POST",
        "/api/groups/",
        [],
        [
            "page",
            "page_size",
            "ordering",
            "name__istartswith",
            "name__iendswith",
            "name__icontains",
            "name__iexact",
            "additional_filters"
        ]
    ],
    "list_logs": [
        "GET",
        "/api/logs/",
        [],
        []
    ],
    "list_mail_accounts": [
        "POST",
        "/api/mail_accounts/",
        [],
        [
            "page",
            "page_size",
            "full_perms",
            "additional_filters"
        ]
    ],
    "list_mail_rules": [
        "POST",
        "/api/mail_rules/",
        [],
        [
            "page",
            "page_size",
            "full_perms",
            "additional_filters"
        ]
    ],
    "list_processed_mail": [
        "POST",
        "/api/processed_mail/",
        [],
        [
            "page",
            "page_size",
            "ordering",
            "rule",
            "status",
            "additional_filters"
        ]
    ],
    "list_saved_views": [
        "GET",
        "/saved_views",
        [],
        [
            "full_perms",
            "page",
            "page_size",
            "ordering",
            "additional_filters"
        ]
    ],
    "list_share_link_bundles": [
        "GET",
        "/share_link_bundles",
        [],
        [
            "page",
            "page_size",
            "ordering",
            "status",
            "documents",
            "created__year",
            "created__month",
            "created__day",
            "created__gt",
            "created__gte",
            "created__lt",
            "created__lte",
            "created__date__gt",
            "created__date__gte",
            "created__date__lt",
            "created__date__lte",
            "expiration__year",
            "expiration__month",
            "expiration__day",
            "expiration__gt",
            "expiration__gte",
            "expiration__lt",
            "expiration__lte",
            "expiration__date__gt",
            "expiration__date__gte",
            "expiration__date__lt",
            "expiration__date__lte",
            "additional_filters"
        ]
    ],
    "list_share_links": [
        "GET",
        "/share_links",
        [],
        [
            "page",
            "page_size",
            "ordering",
            "created__year",
            "created__month",
            "created__day",
            "created__gt",
            "created__gte",
            "created__lt",
            "created__lte",
            "created__date__gt",
            "created__date__gte",
            "created__date__lt",
            "created__date__lte",
            "expiration__year",
            "expiration__month",
            "expiration__day",
            "expiration__gt",
            "expiration__gte",
            "expiration__lt",
            "expiration__lte",
            "expiration__date__gt",
            "expiration__date__gte",
            "expiration__date__lt",
            "expiration__date__lte",
            "additional_filters"
        ]
    ],
    "list_storage_paths": [
        "GET",
        "/storage_paths",
        [],
        [
            "id",
            "id__in",
            "name__icontains",
            "name__iexact",
            "name__istartswith",
            "name__iendswith",
            "path__icontains",
            "path__iexact",
            "path__istartswith",
            "path__iendswith",
            "full_perms",
            "page",
            "page_size",
            "ordering",
            "additional_filters"
        ]
    ],
    "list_tags": [
        "GET",
        "/tags",
        [],
        [
            "id",
            "id__in",
            "name__icontains",
            "name__iexact",
            "name__istartswith",
            "name__iendswith",
            "is_root",
            "full_perms",
            "page",
            "page_size",
            "ordering",
            "additional_filters"
        ]
    ],
    "list_tasks": [
        "POST",
        "/api/tasks/",
        [],
        [
            "page",
            "page_size",
            "ordering",
            "task_id",
            "name",
            "result",
            "task_type",
            "trigger_source",
            "acknowledged",
            "owner",
            "date_created_after",
            "date_created_before",
            "status",
            "is_complete",
            "additional_filters"
        ]
    ],
    "list_trash": [
        "POST",
        "/api/trash/",
        [],
        [
            "page",
            "page_size",
            "full_perms"
        ]
    ],
    "list_users": [
        "POST",
        "/api/users/",
        [],
        [
            "page",
            "page_size",
            "ordering",
            "username__istartswith",
            "username__iendswith",
            "username__icontains",
            "username__iexact",
            "additional_filters"
        ]
    ],
    "list_workflow_actions": [
        "GET",
        "/workflow_actions",
        [],
        [
            "page",
            "page_size",
            "additional_filters"
        ]
    ],
    "list_workflow_triggers": [
        "POST",
        "/workflow_triggers",
        [],
        [
            "page",
            "page_size",
            "additional_filters"
        ]
    ],
    "list_workflows": [
        "GET",
        "/workflows",
        [],
        [
            "page",
            "page_size",
            "additional_filters"
        ]
    ],
    "merge_documents": [
        "POST",
        "/api/documents/bulk_download/",
        [],
        [
            "documents",
            "metadata_document_id",
            "delete_originals",
            "archive_fallback",
            "source_mode"
        ]
    ],
    "merge_documents_as_versions": [
        "POST",
        "/api/documents/bulk_download/",
        [],
        [
            "documents",
            "root_document_id",
            "version_label"
        ]
    ],
    "process_mail_account": [
        "POST",
        "/api/mail_accounts/{id}/process/",
        [
            "id"
        ],
        []
    ],
    "rebuild_share_link_bundle": [
        "POST",
        "{shareLinkBundlesPath}{id}/rebuild/",
        [
            "shareLinkBundlesPath",
            "id"
        ],
        []
    ],
    "remove_document_password": [
        "POST",
        "/api/documents/bulk_download/",
        [],
        [
            "documents",
            "password",
            "update_document",
            "include_metadata",
            "delete_original",
            "source_mode"
        ]
    ],
    "reprocess_documents": [
        "GET",
        "/reprocess_documents",
        [],
        [
            "documents",
            "all",
            "filters",
            "remote_ocr"
        ]
    ],
    "restore_trash_documents": [
        "POST",
        "/api/documents/chat/",
        [],
        [
            "documents"
        ]
    ],
    "rotate_documents": [
        "GET",
        "/rotate_documents",
        [],
        [
            "documents",
            "all",
            "filters",
            "degrees",
            "source_mode"
        ]
    ],
    "run_task": [
        "POST",
        "/api/tasks/run/",
        [],
        [
            "task_type"
        ]
    ],
    "test_mail_account": [
        "POST",
        "/api/mail_accounts/test/",
        [],
        [
            "id",
            "imap_server",
            "imap_port",
            "imap_security",
            "username",
            "password",
            "character_set",
            "is_token",
            "account_type",
            "expiration"
        ]
    ],
    "test_storage_path": [
        "POST",
        "/api/storage_paths/test/",
        [],
        [
            "path",
            "document"
        ]
    ],
    "update_application_config": [
        "PATCH",
        "/api/config/{configId}/",
        [
            "configId"
        ],
        [
            "id",
            "values"
        ]
    ],
    "update_correspondent": [
        "PATCH",
        "/correspondent",
        [],
        [
            "id",
            "name",
            "match",
            "matching_algorithm",
            "is_insensitive",
            "owner",
            "set_permissions"
        ]
    ],
    "update_custom_field": [
        "PATCH",
        "/custom_field",
        [],
        [
            "id",
            "name",
            "data_type",
            "extra_data"
        ]
    ],
    "update_document": [
        "PATCH",
        "/api/documents/{documentId}/",
        [
            "documentId"
        ],
        [
            "id",
            "version",
            "title",
            "content",
            "correspondent",
            "document_type",
            "storage_path",
            "tags",
            "created",
            "archive_serial_number",
            "custom_fields",
            "remove_inbox_tags",
            "owner",
            "set_permissions"
        ]
    ],
    "update_document_type": [
        "PATCH",
        "/document_type",
        [],
        [
            "id",
            "name",
            "match",
            "matching_algorithm",
            "is_insensitive",
            "owner",
            "set_permissions"
        ]
    ],
    "update_document_version": [
        "DELETE",
        "/api/documents/{documentId}/versions/{versionId}/",
        [
            "documentId",
            "versionId"
        ],
        [
            "id",
            "file",
            "fileName",
            "version_label"
        ]
    ],
    "update_document_version_label": [
        "PATCH",
        "/api/documents/{documentId}/versions/{versionId}/",
        [
            "documentId",
            "versionId"
        ],
        [
            "id",
            "version_id",
            "version_label"
        ]
    ],
    "update_group": [
        "PATCH",
        "/api/groups/{id}/",
        [
            "id"
        ],
        [
            "name",
            "permissions"
        ]
    ],
    "update_mail_account": [
        "PATCH",
        "/api/mail_accounts/{id}/",
        [
            "id"
        ],
        [
            "name",
            "imap_server",
            "imap_port",
            "imap_security",
            "username",
            "password",
            "character_set",
            "is_token",
            "account_type",
            "expiration",
            "owner",
            "set_permissions"
        ]
    ],
    "update_mail_rule": [
        "PATCH",
        "/api/mail_rules/{id}/",
        [
            "id"
        ],
        [
            "name",
            "account",
            "folder",
            "filter_from",
            "filter_to",
            "filter_subject",
            "filter_body",
            "filter_attachment_filename_include",
            "filter_attachment_filename_exclude",
            "maximum_age",
            "action",
            "action_parameter",
            "assign_title_from",
            "assign_tags",
            "assign_correspondent_from",
            "assign_correspondent",
            "assign_document_type",
            "assign_owner_from_rule",
            "order",
            "attachment_type",
            "consumption_scope",
            "pdf_layout",
            "enabled",
            "stop_processing",
            "owner",
            "set_permissions"
        ]
    ],
    "update_profile": [
        "PATCH",
        "/api/profile/",
        [],
        [
            "email",
            "password",
            "first_name",
            "last_name"
        ]
    ],
    "update_saved_view": [
        "PATCH",
        "/saved_view",
        [],
        [
            "id",
            "name",
            "icon",
            "sort_field",
            "sort_reverse",
            "filter_rules",
            "page_size",
            "display_mode",
            "display_fields",
            "owner",
            "set_permissions"
        ]
    ],
    "update_storage_path": [
        "PATCH",
        "/storage_path",
        [],
        [
            "id",
            "name",
            "path",
            "match",
            "matching_algorithm",
            "is_insensitive",
            "owner",
            "set_permissions"
        ]
    ],
    "update_tag": [
        "PATCH",
        "/tag",
        [],
        [
            "id",
            "name",
            "color",
            "match",
            "matching_algorithm",
            "is_insensitive",
            "is_inbox_tag",
            "parent",
            "owner",
            "set_permissions"
        ]
    ],
    "update_ui_settings": [
        "POST",
        "/api/ui_settings/",
        [],
        [
            "settings"
        ]
    ],
    "update_user": [
        "PATCH",
        "/api/users/{id}/",
        [
            "id"
        ],
        [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
            "is_superuser",
            "groups",
            "user_permissions"
        ]
    ],
    "update_workflow": [
        "PATCH",
        "/workflow",
        [],
        [
            "id",
            "name",
            "order",
            "enabled",
            "triggers",
            "actions"
        ]
    ],
    "update_workflow_action": [
        "PATCH",
        "/workflow_action",
        [],
        [
            "id",
            "type",
            "assign_title",
            "assign_tags",
            "assign_correspondent",
            "assign_document_type",
            "assign_storage_path",
            "assign_owner",
            "assign_view_users",
            "assign_view_groups",
            "assign_change_users",
            "assign_change_groups",
            "assign_custom_fields",
            "assign_custom_fields_values",
            "remove_all_tags",
            "remove_tags",
            "remove_all_correspondents",
            "remove_correspondents",
            "remove_all_document_types",
            "remove_document_types",
            "remove_all_storage_paths",
            "remove_storage_paths",
            "remove_custom_fields",
            "remove_all_custom_fields",
            "remove_all_owners",
            "remove_owners",
            "remove_all_permissions",
            "remove_view_users",
            "remove_view_groups",
            "remove_change_users",
            "remove_change_groups",
            "email",
            "webhook",
            "passwords",
            "ai_suggestion_fields",
            "ai_create_missing",
            "ai_overwrite_existing"
        ]
    ],
    "update_workflow_trigger": [
        "POST",
        "/workflow_trigger",
        [],
        [
            "id",
            "type",
            "sources",
            "filter_path",
            "filter_filename",
            "filter_mailrule",
            "matching_algorithm",
            "match",
            "is_insensitive",
            "filter_has_tags",
            "filter_has_all_tags",
            "filter_has_not_tags",
            "filter_custom_field_query",
            "filter_has_any_correspondents",
            "filter_has_not_correspondents",
            "filter_has_any_document_types",
            "filter_has_not_document_types",
            "filter_has_any_storage_paths",
            "filter_has_not_storage_paths",
            "filter_has_correspondent",
            "filter_has_document_type",
            "filter_has_storage_path",
            "schedule_offset_days",
            "schedule_is_recurring",
            "schedule_recurring_interval_days",
            "schedule_date_field",
            "schedule_date_custom_field"
        ]
    ],
    "upload_document": [
        "POST",
        "/api/documents/post_document/",
        [],
        [
            "file",
            "fileName",
            "title",
            "created",
            "correspondent",
            "document_type",
            "storage_path",
            "tags",
            "archive_serial_number",
            "custom_fields"
        ]
    ]
}

class PaperlessNgxDynamicAction(Action):
    def __init__(self, action_dict: Dict[str, Any]):
        super().__init__(
            id=action_dict["id"],
            name=action_dict["name"],
            description=action_dict.get("description", ""),
            input_schema=action_dict.get("inputSchema") or action_dict.get("input_schema") or {"type": "object", "properties": {}},
            output_schema=action_dict.get("outputSchema") or action_dict.get("output_schema") or {"type": "object", "properties": {}},
            required_scopes=action_dict.get("requiredScopes") or action_dict.get("required_scopes") or []
        )
        self.raw_dict = action_dict

    async def execute(self, credential: Dict[str, Any], params: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        action_name = self.name
        route_meta = ROUTES.get(action_name, ["GET", f"/{action_name}", [], []])
        method = route_meta[0]
        path_template = route_meta[1]
        path_param_names = route_meta[2]
        body_param_names = route_meta[3]

        url_path = path_template
        for p in path_param_names:
            if p in params:
                val = str(params[p])
                url_path = url_path.replace("{" + p + "}", urllib.parse.quote(val, safe=""))

        url_path = re.sub(r"\{[a-zA-Z0-9_]+\}", "default", url_path)

        base_url = _resolve_base_url(cred)
        if base_url.endswith("/") and url_path.startswith("/"):
            full_url = base_url + url_path[1:]
        elif not base_url.endswith("/") and not url_path.startswith("/"):
            full_url = base_url + "/" + url_path
        else:
            full_url = base_url + url_path

        assert_public_url(full_url)
        headers = _build_headers(cred)

        req_params: Dict[str, Any] = {}
        req_json: Optional[Dict[str, Any]] = None

        if method in ["GET", "DELETE"]:
            for k in body_param_names:
                if k in params and params[k] is not None:
                    req_params[k] = params[k]
            for k, v in params.items():
                if k not in path_param_names and k not in req_params:
                    req_params[k] = v
        else:
            req_json = {}
            for k in body_param_names:
                if k in params and params[k] is not None:
                    req_json[k] = params[k]
            for k, v in params.items():
                if k not in path_param_names and k not in req_json:
                    req_json[k] = v

        resp = await execute_guarded_request(
            client=client,
            method=method,
            url=full_url,
            headers=headers,
            params=req_params if req_params else None,
            json=req_json if req_json else None
        )

        if resp.status_code >= 400:
            raise ValueError(f"Paperless-ngx API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class PaperlessNgxProvider(Provider):
    def __init__(self):
        super().__init__(
            service="paperless_ngx",
            display_name="Paperless-ngx",
            category="Media & Content",
            auth_types=["api_key"],
            description="Paperless-ngx open-source document management system with 139 actions for document OCR, workflows, tags, correspondents, and mail rules."
        )
        for act in get_provider_actions("paperless_ngx"):
            self.register_action(PaperlessNgxDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://{{host}}/api/documents/?page_size=1"
        for key in ["site", "domain", "subdomain", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))

        token = _extract_token(cred)
        if "{token}" in val_url:
            val_url = val_url.replace("{token}", token or "invalid-token")

        assert_public_url(val_url)
        headers = _build_headers(cred)

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers
            )
        except Exception as e:
            raise ValueError(f"Paperless-ngx connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Paperless-ngx credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Paperless-ngx validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "paperless_ngx" == "weixin_store" and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid Paperless-ngx credentials: {body.get('errmsg') or resp.text}")
                elif "paperless_ngx" == "xiaohongshu_store" and (body.get("success") is False or body.get("code", 0) != 0):
                    raise ValueError(f"Invalid Paperless-ngx credentials: {body.get('message') or resp.text}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Paperless-ngx Account"
        }
