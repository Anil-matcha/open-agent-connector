"""Optional user accounts: email + password sign-in, emailed verification codes, cookie sessions.

Each account owns one tenant (``users.tenant_id``), so everything the core scopes by tenant is
automatically private to the user. Enabled by ``CONNECTOR_ACCOUNTS_SIGNUP_MODE`` (default: disabled).
"""
