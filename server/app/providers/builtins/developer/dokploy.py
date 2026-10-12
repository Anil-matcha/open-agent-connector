"""
Dokploy Provider for ConnectorHub.
Loads and registers 524 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "{instanceUrl}/api"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serverToken", "restToken", "writeKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["instanceUrl", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
    if base.startswith("{instanceUrl}"):
        inst = str(cred.get("instanceUrl") or cred.get("host") or cred.get("url") or "https://example.com").strip()
        base = base.replace("{instanceUrl}", inst)
    return base

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = _extract_token(cred)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    auth_mode = "Bearer"
    if auth_mode == "Bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "gitea_token":
        if token:
            headers["Authorization"] = f"token {token}"
    elif auth_mode == "zerotier_token":
        if token:
            headers["Authorization"] = f"token {token}"
    elif auth_mode == "n8n_header":
        if token:
            headers["X-N8N-API-KEY"] = token
    elif auth_mode == "readme_basic":
        if token:
            pair = f"{token}:"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "mingdao_auth":
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if cred.get("appKey"):
            headers["X-App-Key"] = str(cred["appKey"])
        if cred.get("sign"):
            headers["X-Sign"] = str(cred["sign"])

    return headers

ROUTES: Dict[str, List[Any]] = {
    "admin-setupMonitoring": [
        "POST",
        "/admin.setupMonitoring",
        [],
        [
            "metricsConfig"
        ]
    ],
    "ai-analyzeLogs": [
        "POST",
        "/ai.analyzeLogs",
        [],
        [
            "aiId",
            "logs",
            "context"
        ]
    ],
    "ai-create": [
        "POST",
        "/ai.create",
        [],
        [
            "name",
            "apiUrl",
            "apiKey",
            "model",
            "isEnabled"
        ]
    ],
    "ai-delete": [
        "POST",
        "/ai.delete",
        [],
        [
            "aiId"
        ]
    ],
    "ai-deploy": [
        "POST",
        "/ai.deploy",
        [],
        [
            "environmentId",
            "id",
            "dockerCompose",
            "envVariables",
            "serverId",
            "name",
            "description",
            "domains",
            "configFiles"
        ]
    ],
    "ai-get": [
        "GET",
        "/ai.get",
        [],
        [
            "aiId"
        ]
    ],
    "ai-getAll": [
        "GET",
        "/ai.getAll",
        [],
        []
    ],
    "ai-getEnabledProviders": [
        "GET",
        "/ai.getEnabledProviders",
        [],
        []
    ],
    "ai-getModels": [
        "GET",
        "/ai.getModels",
        [],
        [
            "apiUrl",
            "apiKey"
        ]
    ],
    "ai-one": [
        "GET",
        "/ai.one",
        [],
        [
            "aiId"
        ]
    ],
    "ai-suggest": [
        "POST",
        "/ai.suggest",
        [],
        [
            "aiId",
            "input",
            "serverId"
        ]
    ],
    "ai-testConnection": [
        "POST",
        "/ai.testConnection",
        [],
        [
            "apiUrl",
            "apiKey",
            "model"
        ]
    ],
    "ai-update": [
        "POST",
        "/ai.update",
        [],
        [
            "aiId",
            "name",
            "apiUrl",
            "apiKey",
            "model",
            "isEnabled",
            "createdAt"
        ]
    ],
    "application-cancelDeployment": [
        "POST",
        "/application.cancelDeployment",
        [],
        [
            "applicationId"
        ]
    ],
    "application-cleanQueues": [
        "POST",
        "/application.cleanQueues",
        [],
        [
            "applicationId"
        ]
    ],
    "application-clearDeployments": [
        "POST",
        "/application.clearDeployments",
        [],
        [
            "applicationId"
        ]
    ],
    "application-create": [
        "POST",
        "/application.create",
        [],
        [
            "name",
            "appName",
            "description",
            "environmentId",
            "serverId"
        ]
    ],
    "application-delete": [
        "POST",
        "/application.delete",
        [],
        [
            "applicationId"
        ]
    ],
    "application-deploy": [
        "POST",
        "/application.deploy",
        [],
        [
            "applicationId",
            "title",
            "description"
        ]
    ],
    "application-disconnectGitProvider": [
        "POST",
        "/application.disconnectGitProvider",
        [],
        [
            "applicationId"
        ]
    ],
    "application-dropDeployment": [
        "POST",
        "/application.dropDeployment",
        [],
        [
            "applicationId",
            "zip",
            "dropBuildPath"
        ]
    ],
    "application-killBuild": [
        "POST",
        "/application.killBuild",
        [],
        [
            "applicationId"
        ]
    ],
    "application-markRunning": [
        "POST",
        "/application.markRunning",
        [],
        [
            "applicationId"
        ]
    ],
    "application-move": [
        "POST",
        "/application.move",
        [],
        [
            "applicationId",
            "targetEnvironmentId"
        ]
    ],
    "application-one": [
        "GET",
        "/application.one",
        [],
        [
            "applicationId"
        ]
    ],
    "application-readAppMonitoring": [
        "GET",
        "/application.readAppMonitoring",
        [],
        [
            "appName"
        ]
    ],
    "application-readLogs": [
        "GET",
        "/application.readLogs",
        [],
        [
            "applicationId",
            "tail",
            "since",
            "search"
        ]
    ],
    "application-readTraefikConfig": [
        "GET",
        "/application.readTraefikConfig",
        [],
        [
            "applicationId"
        ]
    ],
    "application-redeploy": [
        "POST",
        "/application.redeploy",
        [],
        [
            "applicationId",
            "title",
            "description"
        ]
    ],
    "application-refreshToken": [
        "POST",
        "/application.refreshToken",
        [],
        [
            "applicationId"
        ]
    ],
    "application-reload": [
        "POST",
        "/application.reload",
        [],
        [
            "appName",
            "applicationId"
        ]
    ],
    "application-saveBitbucketProvider": [
        "POST",
        "/application.saveBitbucketProvider",
        [],
        [
            "bitbucketBranch",
            "bitbucketBuildPath",
            "bitbucketOwner",
            "bitbucketRepository",
            "bitbucketRepositorySlug",
            "bitbucketId",
            "applicationId",
            "enableSubmodules",
            "watchPaths"
        ]
    ],
    "application-saveBuildType": [
        "POST",
        "/application.saveBuildType",
        [],
        [
            "applicationId",
            "buildType",
            "dockerfile",
            "dockerContextPath",
            "dockerBuildStage",
            "herokuVersion",
            "railpackVersion",
            "publishDirectory",
            "isStaticSpa"
        ]
    ],
    "application-saveDockerProvider": [
        "POST",
        "/application.saveDockerProvider",
        [],
        [
            "dockerImage",
            "applicationId",
            "username",
            "password",
            "registryUrl"
        ]
    ],
    "application-saveEnvironment": [
        "POST",
        "/application.saveEnvironment",
        [],
        [
            "applicationId",
            "env",
            "buildArgs",
            "buildSecrets",
            "createEnvFile"
        ]
    ],
    "application-saveGiteaProvider": [
        "POST",
        "/application.saveGiteaProvider",
        [],
        [
            "applicationId",
            "giteaBranch",
            "giteaBuildPath",
            "giteaOwner",
            "giteaRepository",
            "giteaId",
            "enableSubmodules",
            "watchPaths"
        ]
    ],
    "application-saveGithubProvider": [
        "POST",
        "/application.saveGithubProvider",
        [],
        [
            "applicationId",
            "repository",
            "branch",
            "owner",
            "buildPath",
            "githubId",
            "triggerType",
            "enableSubmodules",
            "watchPaths"
        ]
    ],
    "application-saveGitlabProvider": [
        "POST",
        "/application.saveGitlabProvider",
        [],
        [
            "applicationId",
            "gitlabBranch",
            "gitlabBuildPath",
            "gitlabOwner",
            "gitlabRepository",
            "gitlabId",
            "gitlabProjectId",
            "gitlabPathNamespace",
            "enableSubmodules",
            "watchPaths"
        ]
    ],
    "application-saveGitProvider": [
        "POST",
        "/application.saveGitProvider",
        [],
        [
            "customGitBranch",
            "applicationId",
            "customGitBuildPath",
            "customGitUrl",
            "watchPaths",
            "enableSubmodules",
            "customGitSSHKeyId"
        ]
    ],
    "application-search": [
        "GET",
        "/application.search",
        [],
        [
            "q",
            "name",
            "appName",
            "description",
            "repository",
            "owner",
            "dockerImage",
            "projectId",
            "environmentId",
            "limit",
            "offset"
        ]
    ],
    "application-start": [
        "POST",
        "/application.start",
        [],
        [
            "applicationId"
        ]
    ],
    "application-stop": [
        "POST",
        "/application.stop",
        [],
        [
            "applicationId"
        ]
    ],
    "application-update": [
        "POST",
        "/application.update",
        [],
        [
            "applicationId",
            "name",
            "appName",
            "description",
            "env",
            "previewEnv",
            "watchPaths",
            "previewBuildArgs",
            "previewBuildSecrets",
            "previewLabels",
            "previewWildcard",
            "previewPort",
            "previewHttps",
            "previewPath",
            "previewCertificateType",
            "previewCustomCertResolver",
            "previewLimit",
            "isPreviewDeploymentsActive",
            "previewRequireCollaboratorPermissions",
            "rollbackActive",
            "buildArgs",
            "buildSecrets",
            "memoryReservation",
            "memoryLimit",
            "cpuReservation",
            "cpuLimit",
            "title",
            "enabled",
            "subtitle",
            "command",
            "args",
            "icon",
            "refreshToken",
            "sourceType",
            "cleanCache",
            "repository",
            "owner",
            "branch",
            "buildPath",
            "triggerType",
            "autoDeploy",
            "gitlabProjectId",
            "gitlabRepository",
            "gitlabOwner",
            "gitlabBranch",
            "gitlabBuildPath",
            "gitlabPathNamespace",
            "giteaRepository",
            "giteaOwner",
            "giteaBranch",
            "giteaBuildPath",
            "bitbucketRepository",
            "bitbucketRepositorySlug",
            "bitbucketOwner",
            "bitbucketBranch",
            "bitbucketBuildPath",
            "username",
            "password",
            "dockerImage",
            "registryUrl",
            "customGitUrl",
            "customGitBranch",
            "customGitBuildPath",
            "customGitSSHKeyId",
            "enableSubmodules",
            "dockerfile",
            "dockerContextPath",
            "dockerBuildStage",
            "dropBuildPath",
            "healthCheckSwarm",
            "restartPolicySwarm",
            "placementSwarm",
            "updateConfigSwarm",
            "rollbackConfigSwarm",
            "modeSwarm",
            "labelsSwarm",
            "networkSwarm",
            "stopGracePeriodSwarm",
            "endpointSpecSwarm",
            "ulimitsSwarm",
            "replicas",
            "applicationStatus",
            "buildType",
            "railpackVersion",
            "herokuVersion",
            "publishDirectory",
            "isStaticSpa",
            "createEnvFile",
            "createdAt",
            "registryId",
            "rollbackRegistryId",
            "environmentId",
            "githubId",
            "gitlabId",
            "giteaId",
            "bitbucketId",
            "buildServerId",
            "buildRegistryId"
        ]
    ],
    "application-updateTraefikConfig": [
        "POST",
        "/application.updateTraefikConfig",
        [],
        [
            "applicationId",
            "traefikConfig"
        ]
    ],
    "auditLog-all": [
        "GET",
        "/auditLog.all",
        [],
        [
            "userId",
            "userEmail",
            "resourceName",
            "action",
            "resourceType",
            "from",
            "to",
            "limit",
            "offset"
        ]
    ],
    "backup-create": [
        "POST",
        "/backup.create",
        [],
        [
            "schedule",
            "enabled",
            "prefix",
            "destinationId",
            "keepLatestCount",
            "database",
            "mariadbId",
            "mysqlId",
            "postgresId",
            "mongoId",
            "libsqlId",
            "databaseType",
            "userId",
            "backupType",
            "composeId",
            "serviceName",
            "metadata"
        ]
    ],
    "backup-listBackupFiles": [
        "GET",
        "/backup.listBackupFiles",
        [],
        [
            "destinationId",
            "search",
            "serverId"
        ]
    ],
    "backup-manualBackupCompose": [
        "POST",
        "/backup.manualBackupCompose",
        [],
        [
            "backupId"
        ]
    ],
    "backup-manualBackupLibsql": [
        "POST",
        "/backup.manualBackupLibsql",
        [],
        [
            "backupId"
        ]
    ],
    "backup-manualBackupMariadb": [
        "POST",
        "/backup.manualBackupMariadb",
        [],
        [
            "backupId"
        ]
    ],
    "backup-manualBackupMongo": [
        "POST",
        "/backup.manualBackupMongo",
        [],
        [
            "backupId"
        ]
    ],
    "backup-manualBackupMySql": [
        "POST",
        "/backup.manualBackupMySql",
        [],
        [
            "backupId"
        ]
    ],
    "backup-manualBackupPostgres": [
        "POST",
        "/backup.manualBackupPostgres",
        [],
        [
            "backupId"
        ]
    ],
    "backup-manualBackupWebServer": [
        "POST",
        "/backup.manualBackupWebServer",
        [],
        [
            "backupId"
        ]
    ],
    "backup-one": [
        "GET",
        "/backup.one",
        [],
        [
            "backupId"
        ]
    ],
    "backup-remove": [
        "POST",
        "/backup.remove",
        [],
        [
            "backupId"
        ]
    ],
    "backup-update": [
        "POST",
        "/backup.update",
        [],
        [
            "schedule",
            "enabled",
            "prefix",
            "backupId",
            "destinationId",
            "database",
            "keepLatestCount",
            "serviceName",
            "metadata",
            "databaseType"
        ]
    ],
    "bitbucket-bitbucketProviders": [
        "GET",
        "/bitbucket.bitbucketProviders",
        [],
        []
    ],
    "bitbucket-create": [
        "POST",
        "/bitbucket.create",
        [],
        [
            "bitbucketId",
            "bitbucketUsername",
            "bitbucketEmail",
            "appPassword",
            "apiToken",
            "bitbucketWorkspaceName",
            "gitProviderId",
            "authId",
            "name"
        ]
    ],
    "bitbucket-getBitbucketBranches": [
        "GET",
        "/bitbucket.getBitbucketBranches",
        [],
        [
            "owner",
            "repo",
            "bitbucketId"
        ]
    ],
    "bitbucket-getBitbucketRepositories": [
        "GET",
        "/bitbucket.getBitbucketRepositories",
        [],
        [
            "bitbucketId"
        ]
    ],
    "bitbucket-one": [
        "GET",
        "/bitbucket.one",
        [],
        [
            "bitbucketId"
        ]
    ],
    "bitbucket-testConnection": [
        "POST",
        "/bitbucket.testConnection",
        [],
        [
            "bitbucketId",
            "bitbucketUsername",
            "bitbucketEmail",
            "workspaceName",
            "apiToken",
            "appPassword"
        ]
    ],
    "bitbucket-update": [
        "POST",
        "/bitbucket.update",
        [],
        [
            "bitbucketId",
            "bitbucketUsername",
            "bitbucketEmail",
            "appPassword",
            "apiToken",
            "bitbucketWorkspaceName",
            "gitProviderId",
            "name",
            "organizationId"
        ]
    ],
    "certificates-all": [
        "GET",
        "/certificates.all",
        [],
        []
    ],
    "certificates-create": [
        "POST",
        "/certificates.create",
        [],
        [
            "certificateId",
            "name",
            "certificateData",
            "privateKey",
            "certificatePath",
            "autoRenew",
            "organizationId",
            "serverId"
        ]
    ],
    "certificates-one": [
        "GET",
        "/certificates.one",
        [],
        [
            "certificateId"
        ]
    ],
    "certificates-remove": [
        "POST",
        "/certificates.remove",
        [],
        [
            "certificateId"
        ]
    ],
    "certificates-update": [
        "POST",
        "/certificates.update",
        [],
        [
            "certificateId",
            "name",
            "certificateData",
            "privateKey"
        ]
    ],
    "cluster-addManager": [
        "GET",
        "/cluster.addManager",
        [],
        [
            "serverId"
        ]
    ],
    "cluster-addWorker": [
        "GET",
        "/cluster.addWorker",
        [],
        [
            "serverId"
        ]
    ],
    "cluster-getNodes": [
        "GET",
        "/cluster.getNodes",
        [],
        [
            "serverId"
        ]
    ],
    "cluster-removeWorker": [
        "POST",
        "/cluster.removeWorker",
        [],
        [
            "nodeId",
            "serverId"
        ]
    ],
    "compose-cancelDeployment": [
        "POST",
        "/compose.cancelDeployment",
        [],
        [
            "composeId"
        ]
    ],
    "compose-cleanQueues": [
        "POST",
        "/compose.cleanQueues",
        [],
        [
            "composeId"
        ]
    ],
    "compose-clearDeployments": [
        "POST",
        "/compose.clearDeployments",
        [],
        [
            "composeId"
        ]
    ],
    "compose-create": [
        "POST",
        "/compose.create",
        [],
        [
            "name",
            "description",
            "environmentId",
            "composeType",
            "appName",
            "serverId",
            "composeFile"
        ]
    ],
    "compose-delete": [
        "POST",
        "/compose.delete",
        [],
        [
            "composeId",
            "deleteVolumes"
        ]
    ],
    "compose-deploy": [
        "POST",
        "/compose.deploy",
        [],
        [
            "composeId",
            "title",
            "description"
        ]
    ],
    "compose-deployTemplate": [
        "POST",
        "/compose.deployTemplate",
        [],
        [
            "environmentId",
            "serverId",
            "id",
            "baseUrl"
        ]
    ],
    "compose-disconnectGitProvider": [
        "POST",
        "/compose.disconnectGitProvider",
        [],
        [
            "composeId"
        ]
    ],
    "compose-fetchSourceType": [
        "POST",
        "/compose.fetchSourceType",
        [],
        [
            "composeId"
        ]
    ],
    "compose-getConvertedCompose": [
        "GET",
        "/compose.getConvertedCompose",
        [],
        [
            "composeId"
        ]
    ],
    "compose-getDefaultCommand": [
        "GET",
        "/compose.getDefaultCommand",
        [],
        [
            "composeId"
        ]
    ],
    "compose-getTags": [
        "GET",
        "/compose.getTags",
        [],
        [
            "baseUrl"
        ]
    ],
    "compose-import": [
        "POST",
        "/compose.import",
        [],
        [
            "base64",
            "composeId"
        ]
    ],
    "compose-isolatedDeployment": [
        "POST",
        "/compose.isolatedDeployment",
        [],
        [
            "composeId",
            "suffix"
        ]
    ],
    "compose-killBuild": [
        "POST",
        "/compose.killBuild",
        [],
        [
            "composeId"
        ]
    ],
    "compose-loadMountsByService": [
        "GET",
        "/compose.loadMountsByService",
        [],
        [
            "composeId",
            "serviceName"
        ]
    ],
    "compose-loadServices": [
        "GET",
        "/compose.loadServices",
        [],
        [
            "composeId",
            "type"
        ]
    ],
    "compose-move": [
        "POST",
        "/compose.move",
        [],
        [
            "composeId",
            "targetEnvironmentId"
        ]
    ],
    "compose-one": [
        "GET",
        "/compose.one",
        [],
        [
            "composeId"
        ]
    ],
    "compose-processTemplate": [
        "POST",
        "/compose.processTemplate",
        [],
        [
            "base64",
            "composeId"
        ]
    ],
    "compose-randomizeCompose": [
        "POST",
        "/compose.randomizeCompose",
        [],
        [
            "composeId",
            "suffix"
        ]
    ],
    "compose-readLogs": [
        "GET",
        "/compose.readLogs",
        [],
        [
            "composeId",
            "containerId",
            "tail",
            "since",
            "search"
        ]
    ],
    "compose-redeploy": [
        "POST",
        "/compose.redeploy",
        [],
        [
            "composeId",
            "title",
            "description"
        ]
    ],
    "compose-refreshToken": [
        "POST",
        "/compose.refreshToken",
        [],
        [
            "composeId"
        ]
    ],
    "compose-saveEnvironment": [
        "POST",
        "/compose.saveEnvironment",
        [],
        [
            "composeId",
            "env"
        ]
    ],
    "compose-search": [
        "GET",
        "/compose.search",
        [],
        [
            "q",
            "name",
            "appName",
            "description",
            "projectId",
            "environmentId",
            "limit",
            "offset"
        ]
    ],
    "compose-start": [
        "POST",
        "/compose.start",
        [],
        [
            "composeId"
        ]
    ],
    "compose-stop": [
        "POST",
        "/compose.stop",
        [],
        [
            "composeId"
        ]
    ],
    "compose-templates": [
        "GET",
        "/compose.templates",
        [],
        [
            "baseUrl"
        ]
    ],
    "compose-update": [
        "POST",
        "/compose.update",
        [],
        [
            "composeId",
            "name",
            "appName",
            "description",
            "env",
            "composeFile",
            "refreshToken",
            "sourceType",
            "composeType",
            "repository",
            "owner",
            "branch",
            "autoDeploy",
            "gitlabProjectId",
            "gitlabRepository",
            "gitlabOwner",
            "gitlabBranch",
            "gitlabPathNamespace",
            "bitbucketRepository",
            "bitbucketRepositorySlug",
            "bitbucketOwner",
            "bitbucketBranch",
            "giteaRepository",
            "giteaOwner",
            "giteaBranch",
            "customGitUrl",
            "customGitBranch",
            "customGitSSHKeyId",
            "command",
            "enableSubmodules",
            "composePath",
            "suffix",
            "randomize",
            "isolatedDeployment",
            "isolatedDeploymentsVolume",
            "triggerType",
            "composeStatus",
            "environmentId",
            "createdAt",
            "watchPaths",
            "githubId",
            "gitlabId",
            "bitbucketId",
            "giteaId"
        ]
    ],
    "customRole-all": [
        "GET",
        "/customRole.all",
        [],
        []
    ],
    "customRole-create": [
        "POST",
        "/customRole.create",
        [],
        [
            "roleName",
            "permissions"
        ]
    ],
    "customRole-getStatements": [
        "GET",
        "/customRole.getStatements",
        [],
        []
    ],
    "customRole-membersByRole": [
        "GET",
        "/customRole.membersByRole",
        [],
        [
            "roleName"
        ]
    ],
    "customRole-remove": [
        "POST",
        "/customRole.remove",
        [],
        [
            "roleName"
        ]
    ],
    "customRole-update": [
        "POST",
        "/customRole.update",
        [],
        [
            "roleName",
            "newRoleName",
            "permissions"
        ]
    ],
    "deployment-all": [
        "GET",
        "/deployment.all",
        [],
        [
            "applicationId"
        ]
    ],
    "deployment-allByCompose": [
        "GET",
        "/deployment.allByCompose",
        [],
        [
            "composeId"
        ]
    ],
    "deployment-allByServer": [
        "GET",
        "/deployment.allByServer",
        [],
        [
            "serverId"
        ]
    ],
    "deployment-allByType": [
        "GET",
        "/deployment.allByType",
        [],
        [
            "id",
            "type"
        ]
    ],
    "deployment-allCentralized": [
        "GET",
        "/deployment.allCentralized",
        [],
        []
    ],
    "deployment-killProcess": [
        "POST",
        "/deployment.killProcess",
        [],
        [
            "deploymentId"
        ]
    ],
    "deployment-queueList": [
        "GET",
        "/deployment.queueList",
        [],
        []
    ],
    "deployment-removeDeployment": [
        "POST",
        "/deployment.removeDeployment",
        [],
        [
            "deploymentId"
        ]
    ],
    "destination-all": [
        "GET",
        "/destination.all",
        [],
        []
    ],
    "destination-create": [
        "POST",
        "/destination.create",
        [],
        [
            "name",
            "provider",
            "accessKey",
            "bucket",
            "region",
            "endpoint",
            "secretAccessKey",
            "additionalFlags",
            "serverId"
        ]
    ],
    "destination-one": [
        "GET",
        "/destination.one",
        [],
        [
            "destinationId"
        ]
    ],
    "destination-remove": [
        "POST",
        "/destination.remove",
        [],
        [
            "destinationId"
        ]
    ],
    "destination-testConnection": [
        "POST",
        "/destination.testConnection",
        [],
        [
            "name",
            "provider",
            "accessKey",
            "bucket",
            "region",
            "endpoint",
            "secretAccessKey",
            "additionalFlags",
            "serverId"
        ]
    ],
    "destination-update": [
        "POST",
        "/destination.update",
        [],
        [
            "name",
            "accessKey",
            "bucket",
            "region",
            "endpoint",
            "secretAccessKey",
            "destinationId",
            "provider",
            "additionalFlags",
            "serverId"
        ]
    ],
    "docker-getConfig": [
        "GET",
        "/docker.getConfig",
        [],
        [
            "containerId",
            "serverId"
        ]
    ],
    "docker-getContainers": [
        "GET",
        "/docker.getContainers",
        [],
        [
            "serverId"
        ]
    ],
    "docker-getContainersByAppLabel": [
        "GET",
        "/docker.getContainersByAppLabel",
        [],
        [
            "appName",
            "serverId",
            "type"
        ]
    ],
    "docker-getContainersByAppNameMatch": [
        "GET",
        "/docker.getContainersByAppNameMatch",
        [],
        [
            "appType",
            "appName",
            "serverId"
        ]
    ],
    "docker-getServiceContainersByAppName": [
        "GET",
        "/docker.getServiceContainersByAppName",
        [],
        [
            "appName",
            "serverId"
        ]
    ],
    "docker-getStackContainersByAppName": [
        "GET",
        "/docker.getStackContainersByAppName",
        [],
        [
            "appName",
            "serverId"
        ]
    ],
    "docker-killContainer": [
        "POST",
        "/docker.killContainer",
        [],
        [
            "containerId",
            "serverId"
        ]
    ],
    "docker-removeContainer": [
        "POST",
        "/docker.removeContainer",
        [],
        [
            "containerId",
            "serverId"
        ]
    ],
    "docker-restartContainer": [
        "POST",
        "/docker.restartContainer",
        [],
        [
            "containerId",
            "serverId"
        ]
    ],
    "docker-startContainer": [
        "POST",
        "/docker.startContainer",
        [],
        [
            "containerId",
            "serverId"
        ]
    ],
    "docker-stopContainer": [
        "POST",
        "/docker.stopContainer",
        [],
        [
            "containerId",
            "serverId"
        ]
    ],
    "docker-uploadFileToContainer": [
        "POST",
        "/docker.uploadFileToContainer",
        [],
        [
            "containerId",
            "file",
            "destinationPath",
            "serverId"
        ]
    ],
    "domain-byApplicationId": [
        "GET",
        "/domain.byApplicationId",
        [],
        [
            "applicationId"
        ]
    ],
    "domain-byComposeId": [
        "GET",
        "/domain.byComposeId",
        [],
        [
            "composeId"
        ]
    ],
    "domain-canGenerateTraefikMeDomains": [
        "GET",
        "/domain.canGenerateTraefikMeDomains",
        [],
        [
            "serverId"
        ]
    ],
    "domain-create": [
        "POST",
        "/domain.create",
        [],
        [
            "host",
            "path",
            "port",
            "customEntrypoint",
            "https",
            "applicationId",
            "certificateType",
            "customCertResolver",
            "composeId",
            "serviceName",
            "domainType",
            "previewDeploymentId",
            "internalPath",
            "stripPath",
            "middlewares"
        ]
    ],
    "domain-delete": [
        "POST",
        "/domain.delete",
        [],
        [
            "domainId"
        ]
    ],
    "domain-generateDomain": [
        "POST",
        "/domain.generateDomain",
        [],
        [
            "appName",
            "serverId"
        ]
    ],
    "domain-one": [
        "GET",
        "/domain.one",
        [],
        [
            "domainId"
        ]
    ],
    "domain-update": [
        "POST",
        "/domain.update",
        [],
        [
            "host",
            "path",
            "port",
            "customEntrypoint",
            "https",
            "certificateType",
            "customCertResolver",
            "serviceName",
            "domainType",
            "internalPath",
            "stripPath",
            "middlewares",
            "domainId"
        ]
    ],
    "domain-validateDomain": [
        "POST",
        "/domain.validateDomain",
        [],
        [
            "domain",
            "serverIp"
        ]
    ],
    "environment-byProjectId": [
        "GET",
        "/environment.byProjectId",
        [],
        [
            "projectId"
        ]
    ],
    "environment-create": [
        "POST",
        "/environment.create",
        [],
        [
            "name",
            "description",
            "projectId"
        ]
    ],
    "environment-duplicate": [
        "POST",
        "/environment.duplicate",
        [],
        [
            "environmentId",
            "name",
            "description"
        ]
    ],
    "environment-one": [
        "GET",
        "/environment.one",
        [],
        [
            "environmentId"
        ]
    ],
    "environment-remove": [
        "POST",
        "/environment.remove",
        [],
        [
            "environmentId"
        ]
    ],
    "environment-search": [
        "GET",
        "/environment.search",
        [],
        [
            "q",
            "name",
            "description",
            "projectId",
            "limit",
            "offset"
        ]
    ],
    "environment-update": [
        "POST",
        "/environment.update",
        [],
        [
            "environmentId",
            "name",
            "description",
            "projectId",
            "env"
        ]
    ],
    "gitea-create": [
        "POST",
        "/gitea.create",
        [],
        [
            "giteaId",
            "giteaUrl",
            "giteaInternalUrl",
            "redirectUri",
            "clientId",
            "clientSecret",
            "gitProviderId",
            "accessToken",
            "refreshToken",
            "expiresAt",
            "scopes",
            "lastAuthenticatedAt",
            "name",
            "giteaUsername",
            "organizationName"
        ]
    ],
    "gitea-getGiteaBranches": [
        "GET",
        "/gitea.getGiteaBranches",
        [],
        [
            "owner",
            "repositoryName",
            "giteaId"
        ]
    ],
    "gitea-getGiteaRepositories": [
        "GET",
        "/gitea.getGiteaRepositories",
        [],
        [
            "giteaId"
        ]
    ],
    "gitea-getGiteaUrl": [
        "GET",
        "/gitea.getGiteaUrl",
        [],
        [
            "giteaId"
        ]
    ],
    "gitea-giteaProviders": [
        "GET",
        "/gitea.giteaProviders",
        [],
        []
    ],
    "gitea-one": [
        "GET",
        "/gitea.one",
        [],
        [
            "giteaId"
        ]
    ],
    "gitea-testConnection": [
        "POST",
        "/gitea.testConnection",
        [],
        [
            "giteaId",
            "organizationName"
        ]
    ],
    "gitea-update": [
        "POST",
        "/gitea.update",
        [],
        [
            "giteaId",
            "giteaUrl",
            "giteaInternalUrl",
            "redirectUri",
            "clientId",
            "clientSecret",
            "gitProviderId",
            "accessToken",
            "refreshToken",
            "expiresAt",
            "scopes",
            "lastAuthenticatedAt",
            "name",
            "giteaUsername",
            "organizationName"
        ]
    ],
    "github-getGithubBranches": [
        "GET",
        "/github.getGithubBranches",
        [],
        [
            "repo",
            "owner",
            "githubId"
        ]
    ],
    "github-getGithubRepositories": [
        "GET",
        "/github.getGithubRepositories",
        [],
        [
            "githubId"
        ]
    ],
    "github-githubProviders": [
        "GET",
        "/github.githubProviders",
        [],
        []
    ],
    "github-one": [
        "GET",
        "/github.one",
        [],
        [
            "githubId"
        ]
    ],
    "github-testConnection": [
        "POST",
        "/github.testConnection",
        [],
        [
            "githubId"
        ]
    ],
    "github-update": [
        "POST",
        "/github.update",
        [],
        [
            "githubId",
            "name",
            "gitProviderId",
            "githubAppName"
        ]
    ],
    "gitlab-create": [
        "POST",
        "/gitlab.create",
        [],
        [
            "applicationId",
            "secret",
            "groupName",
            "gitProviderId",
            "redirectUri",
            "authId",
            "name",
            "gitlabUrl",
            "gitlabInternalUrl"
        ]
    ],
    "gitlab-getGitlabBranches": [
        "GET",
        "/gitlab.getGitlabBranches",
        [],
        [
            "id",
            "owner",
            "repo",
            "gitlabId"
        ]
    ],
    "gitlab-getGitlabRepositories": [
        "GET",
        "/gitlab.getGitlabRepositories",
        [],
        [
            "gitlabId"
        ]
    ],
    "gitlab-gitlabProviders": [
        "GET",
        "/gitlab.gitlabProviders",
        [],
        []
    ],
    "gitlab-one": [
        "GET",
        "/gitlab.one",
        [],
        [
            "gitlabId"
        ]
    ],
    "gitlab-testConnection": [
        "POST",
        "/gitlab.testConnection",
        [],
        [
            "gitlabId",
            "groupName"
        ]
    ],
    "gitlab-update": [
        "POST",
        "/gitlab.update",
        [],
        [
            "applicationId",
            "secret",
            "groupName",
            "redirectUri",
            "name",
            "gitlabId",
            "gitlabUrl",
            "gitProviderId",
            "gitlabInternalUrl"
        ]
    ],
    "gitProvider-allForPermissions": [
        "GET",
        "/gitProvider.allForPermissions",
        [],
        []
    ],
    "gitProvider-getAll": [
        "GET",
        "/gitProvider.getAll",
        [],
        []
    ],
    "gitProvider-remove": [
        "POST",
        "/gitProvider.remove",
        [],
        [
            "gitProviderId"
        ]
    ],
    "gitProvider-toggleShare": [
        "POST",
        "/gitProvider.toggleShare",
        [],
        [
            "gitProviderId",
            "sharedWithOrganization"
        ]
    ],
    "libsql-changeStatus": [
        "POST",
        "/libsql.changeStatus",
        [],
        [
            "libsqlId",
            "applicationStatus"
        ]
    ],
    "libsql-create": [
        "POST",
        "/libsql.create",
        [],
        [
            "name",
            "appName",
            "dockerImage",
            "environmentId",
            "description",
            "databaseUser",
            "databasePassword",
            "sqldNode",
            "sqldPrimaryUrl",
            "enableNamespaces",
            "serverId"
        ]
    ],
    "libsql-deploy": [
        "POST",
        "/libsql.deploy",
        [],
        [
            "libsqlId"
        ]
    ],
    "libsql-move": [
        "POST",
        "/libsql.move",
        [],
        [
            "libsqlId",
            "targetEnvironmentId"
        ]
    ],
    "libsql-one": [
        "GET",
        "/libsql.one",
        [],
        [
            "libsqlId"
        ]
    ],
    "libsql-readLogs": [
        "GET",
        "/libsql.readLogs",
        [],
        [
            "libsqlId",
            "tail",
            "since",
            "search"
        ]
    ],
    "libsql-rebuild": [
        "POST",
        "/libsql.rebuild",
        [],
        [
            "libsqlId"
        ]
    ],
    "libsql-reload": [
        "POST",
        "/libsql.reload",
        [],
        [
            "libsqlId",
            "appName"
        ]
    ],
    "libsql-remove": [
        "POST",
        "/libsql.remove",
        [],
        [
            "libsqlId"
        ]
    ],
    "libsql-saveEnvironment": [
        "POST",
        "/libsql.saveEnvironment",
        [],
        [
            "libsqlId",
            "env"
        ]
    ],
    "libsql-saveExternalPorts": [
        "POST",
        "/libsql.saveExternalPorts",
        [],
        [
            "libsqlId",
            "externalPort",
            "externalGRPCPort",
            "externalAdminPort"
        ]
    ],
    "libsql-start": [
        "POST",
        "/libsql.start",
        [],
        [
            "libsqlId"
        ]
    ],
    "libsql-stop": [
        "POST",
        "/libsql.stop",
        [],
        [
            "libsqlId"
        ]
    ],
    "libsql-update": [
        "POST",
        "/libsql.update",
        [],
        [
            "libsqlId",
            "name",
            "appName",
            "description",
            "databaseUser",
            "databasePassword",
            "sqldNode",
            "sqldPrimaryUrl",
            "enableNamespaces",
            "dockerImage",
            "command",
            "env",
            "memoryReservation",
            "memoryLimit",
            "cpuReservation",
            "cpuLimit",
            "externalPort",
            "externalGRPCPort",
            "externalAdminPort",
            "applicationStatus",
            "healthCheckSwarm",
            "restartPolicySwarm",
            "placementSwarm",
            "updateConfigSwarm",
            "rollbackConfigSwarm",
            "modeSwarm",
            "labelsSwarm",
            "networkSwarm",
            "stopGracePeriodSwarm",
            "endpointSpecSwarm",
            "replicas",
            "createdAt",
            "environmentId"
        ]
    ],
    "licenseKey-activate": [
        "POST",
        "/licenseKey.activate",
        [],
        [
            "licenseKey"
        ]
    ],
    "licenseKey-deactivate": [
        "POST",
        "/licenseKey.deactivate",
        [],
        []
    ],
    "licenseKey-getEnterpriseSettings": [
        "GET",
        "/licenseKey.getEnterpriseSettings",
        [],
        []
    ],
    "licenseKey-haveValidLicenseKey": [
        "GET",
        "/licenseKey.haveValidLicenseKey",
        [],
        []
    ],
    "licenseKey-updateEnterpriseSettings": [
        "POST",
        "/licenseKey.updateEnterpriseSettings",
        [],
        [
            "enableEnterpriseFeatures"
        ]
    ],
    "licenseKey-validate": [
        "POST",
        "/licenseKey.validate",
        [],
        []
    ],
    "mariadb-changePassword": [
        "POST",
        "/mariadb.changePassword",
        [],
        [
            "mariadbId",
            "password",
            "type"
        ]
    ],
    "mariadb-changeStatus": [
        "POST",
        "/mariadb.changeStatus",
        [],
        [
            "mariadbId",
            "applicationStatus"
        ]
    ],
    "mariadb-create": [
        "POST",
        "/mariadb.create",
        [],
        [
            "name",
            "appName",
            "dockerImage",
            "databaseRootPassword",
            "environmentId",
            "description",
            "databaseName",
            "databaseUser",
            "databasePassword",
            "serverId"
        ]
    ],
    "mariadb-deploy": [
        "POST",
        "/mariadb.deploy",
        [],
        [
            "mariadbId"
        ]
    ],
    "mariadb-move": [
        "POST",
        "/mariadb.move",
        [],
        [
            "mariadbId",
            "targetEnvironmentId"
        ]
    ],
    "mariadb-one": [
        "GET",
        "/mariadb.one",
        [],
        [
            "mariadbId"
        ]
    ],
    "mariadb-readLogs": [
        "GET",
        "/mariadb.readLogs",
        [],
        [
            "mariadbId",
            "tail",
            "since",
            "search"
        ]
    ],
    "mariadb-rebuild": [
        "POST",
        "/mariadb.rebuild",
        [],
        [
            "mariadbId"
        ]
    ],
    "mariadb-reload": [
        "POST",
        "/mariadb.reload",
        [],
        [
            "mariadbId",
            "appName"
        ]
    ],
    "mariadb-remove": [
        "POST",
        "/mariadb.remove",
        [],
        [
            "mariadbId"
        ]
    ],
    "mariadb-saveEnvironment": [
        "POST",
        "/mariadb.saveEnvironment",
        [],
        [
            "mariadbId",
            "env"
        ]
    ],
    "mariadb-saveExternalPort": [
        "POST",
        "/mariadb.saveExternalPort",
        [],
        [
            "mariadbId",
            "externalPort"
        ]
    ],
    "mariadb-search": [
        "GET",
        "/mariadb.search",
        [],
        [
            "q",
            "name",
            "appName",
            "description",
            "projectId",
            "environmentId",
            "limit",
            "offset"
        ]
    ],
    "mariadb-start": [
        "POST",
        "/mariadb.start",
        [],
        [
            "mariadbId"
        ]
    ],
    "mariadb-stop": [
        "POST",
        "/mariadb.stop",
        [],
        [
            "mariadbId"
        ]
    ],
    "mariadb-update": [
        "POST",
        "/mariadb.update",
        [],
        [
            "mariadbId",
            "name",
            "appName",
            "description",
            "databaseName",
            "databaseUser",
            "databasePassword",
            "databaseRootPassword",
            "dockerImage",
            "command",
            "args",
            "env",
            "memoryReservation",
            "memoryLimit",
            "cpuReservation",
            "cpuLimit",
            "externalPort",
            "applicationStatus",
            "healthCheckSwarm",
            "restartPolicySwarm",
            "placementSwarm",
            "updateConfigSwarm",
            "rollbackConfigSwarm",
            "modeSwarm",
            "labelsSwarm",
            "networkSwarm",
            "stopGracePeriodSwarm",
            "endpointSpecSwarm",
            "ulimitsSwarm",
            "replicas",
            "createdAt",
            "environmentId"
        ]
    ],
    "mongo-changePassword": [
        "POST",
        "/mongo.changePassword",
        [],
        [
            "mongoId",
            "password"
        ]
    ],
    "mongo-changeStatus": [
        "POST",
        "/mongo.changeStatus",
        [],
        [
            "mongoId",
            "applicationStatus"
        ]
    ],
    "mongo-create": [
        "POST",
        "/mongo.create",
        [],
        [
            "name",
            "appName",
            "dockerImage",
            "environmentId",
            "description",
            "databaseUser",
            "databasePassword",
            "serverId",
            "replicaSets"
        ]
    ],
    "mongo-deploy": [
        "POST",
        "/mongo.deploy",
        [],
        [
            "mongoId"
        ]
    ],
    "mongo-move": [
        "POST",
        "/mongo.move",
        [],
        [
            "mongoId",
            "targetEnvironmentId"
        ]
    ],
    "mongo-one": [
        "GET",
        "/mongo.one",
        [],
        [
            "mongoId"
        ]
    ],
    "mongo-readLogs": [
        "GET",
        "/mongo.readLogs",
        [],
        [
            "mongoId",
            "tail",
            "since",
            "search"
        ]
    ],
    "mongo-rebuild": [
        "POST",
        "/mongo.rebuild",
        [],
        [
            "mongoId"
        ]
    ],
    "mongo-reload": [
        "POST",
        "/mongo.reload",
        [],
        [
            "mongoId",
            "appName"
        ]
    ],
    "mongo-remove": [
        "POST",
        "/mongo.remove",
        [],
        [
            "mongoId"
        ]
    ],
    "mongo-saveEnvironment": [
        "POST",
        "/mongo.saveEnvironment",
        [],
        [
            "mongoId",
            "env"
        ]
    ],
    "mongo-saveExternalPort": [
        "POST",
        "/mongo.saveExternalPort",
        [],
        [
            "mongoId",
            "externalPort"
        ]
    ],
    "mongo-search": [
        "GET",
        "/mongo.search",
        [],
        [
            "q",
            "name",
            "appName",
            "description",
            "projectId",
            "environmentId",
            "limit",
            "offset"
        ]
    ],
    "mongo-start": [
        "POST",
        "/mongo.start",
        [],
        [
            "mongoId"
        ]
    ],
    "mongo-stop": [
        "POST",
        "/mongo.stop",
        [],
        [
            "mongoId"
        ]
    ],
    "mongo-update": [
        "POST",
        "/mongo.update",
        [],
        [
            "mongoId",
            "name",
            "appName",
            "description",
            "databaseUser",
            "databasePassword",
            "dockerImage",
            "command",
            "args",
            "env",
            "memoryReservation",
            "memoryLimit",
            "cpuReservation",
            "cpuLimit",
            "externalPort",
            "applicationStatus",
            "healthCheckSwarm",
            "restartPolicySwarm",
            "placementSwarm",
            "updateConfigSwarm",
            "rollbackConfigSwarm",
            "modeSwarm",
            "labelsSwarm",
            "networkSwarm",
            "stopGracePeriodSwarm",
            "endpointSpecSwarm",
            "ulimitsSwarm",
            "replicas",
            "createdAt",
            "environmentId",
            "replicaSets"
        ]
    ],
    "mounts-allNamedByApplicationId": [
        "GET",
        "/mounts.allNamedByApplicationId",
        [],
        [
            "applicationId"
        ]
    ],
    "mounts-create": [
        "POST",
        "/mounts.create",
        [],
        [
            "type",
            "hostPath",
            "volumeName",
            "content",
            "mountPath",
            "filePath",
            "serviceType",
            "serviceId"
        ]
    ],
    "mounts-listByServiceId": [
        "GET",
        "/mounts.listByServiceId",
        [],
        [
            "serviceType",
            "serviceId"
        ]
    ],
    "mounts-one": [
        "GET",
        "/mounts.one",
        [],
        [
            "mountId"
        ]
    ],
    "mounts-remove": [
        "POST",
        "/mounts.remove",
        [],
        [
            "mountId"
        ]
    ],
    "mounts-update": [
        "POST",
        "/mounts.update",
        [],
        [
            "mountId",
            "type",
            "hostPath",
            "volumeName",
            "filePath",
            "content",
            "serviceType",
            "mountPath",
            "applicationId",
            "composeId",
            "libsqlId",
            "mariadbId",
            "mongoId",
            "mysqlId",
            "postgresId",
            "redisId"
        ]
    ],
    "mysql-changePassword": [
        "POST",
        "/mysql.changePassword",
        [],
        [
            "mysqlId",
            "password",
            "type"
        ]
    ],
    "mysql-changeStatus": [
        "POST",
        "/mysql.changeStatus",
        [],
        [
            "mysqlId",
            "applicationStatus"
        ]
    ],
    "mysql-create": [
        "POST",
        "/mysql.create",
        [],
        [
            "name",
            "appName",
            "dockerImage",
            "environmentId",
            "description",
            "databaseName",
            "databaseUser",
            "databasePassword",
            "databaseRootPassword",
            "serverId"
        ]
    ],
    "mysql-deploy": [
        "POST",
        "/mysql.deploy",
        [],
        [
            "mysqlId"
        ]
    ],
    "mysql-move": [
        "POST",
        "/mysql.move",
        [],
        [
            "mysqlId",
            "targetEnvironmentId"
        ]
    ],
    "mysql-one": [
        "GET",
        "/mysql.one",
        [],
        [
            "mysqlId"
        ]
    ],
    "mysql-readLogs": [
        "GET",
        "/mysql.readLogs",
        [],
        [
            "mysqlId",
            "tail",
            "since",
            "search"
        ]
    ],
    "mysql-rebuild": [
        "POST",
        "/mysql.rebuild",
        [],
        [
            "mysqlId"
        ]
    ],
    "mysql-reload": [
        "POST",
        "/mysql.reload",
        [],
        [
            "mysqlId",
            "appName"
        ]
    ],
    "mysql-remove": [
        "POST",
        "/mysql.remove",
        [],
        [
            "mysqlId"
        ]
    ],
    "mysql-saveEnvironment": [
        "POST",
        "/mysql.saveEnvironment",
        [],
        [
            "mysqlId",
            "env"
        ]
    ],
    "mysql-saveExternalPort": [
        "POST",
        "/mysql.saveExternalPort",
        [],
        [
            "mysqlId",
            "externalPort"
        ]
    ],
    "mysql-search": [
        "GET",
        "/mysql.search",
        [],
        [
            "q",
            "name",
            "appName",
            "description",
            "projectId",
            "environmentId",
            "limit",
            "offset"
        ]
    ],
    "mysql-start": [
        "POST",
        "/mysql.start",
        [],
        [
            "mysqlId"
        ]
    ],
    "mysql-stop": [
        "POST",
        "/mysql.stop",
        [],
        [
            "mysqlId"
        ]
    ],
    "mysql-update": [
        "POST",
        "/mysql.update",
        [],
        [
            "mysqlId",
            "name",
            "appName",
            "description",
            "databaseName",
            "databaseUser",
            "databasePassword",
            "databaseRootPassword",
            "dockerImage",
            "command",
            "args",
            "env",
            "memoryReservation",
            "memoryLimit",
            "cpuReservation",
            "cpuLimit",
            "externalPort",
            "applicationStatus",
            "healthCheckSwarm",
            "restartPolicySwarm",
            "placementSwarm",
            "updateConfigSwarm",
            "rollbackConfigSwarm",
            "modeSwarm",
            "labelsSwarm",
            "networkSwarm",
            "stopGracePeriodSwarm",
            "endpointSpecSwarm",
            "ulimitsSwarm",
            "replicas",
            "createdAt",
            "environmentId"
        ]
    ],
    "notification-all": [
        "GET",
        "/notification.all",
        [],
        []
    ],
    "notification-createCustom": [
        "POST",
        "/notification.createCustom",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "endpoint",
            "headers"
        ]
    ],
    "notification-createDiscord": [
        "POST",
        "/notification.createDiscord",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "webhookUrl",
            "decoration"
        ]
    ],
    "notification-createEmail": [
        "POST",
        "/notification.createEmail",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "smtpServer",
            "smtpPort",
            "username",
            "password",
            "fromAddress",
            "toAddresses"
        ]
    ],
    "notification-createGotify": [
        "POST",
        "/notification.createGotify",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverUrl",
            "appToken",
            "priority",
            "decoration"
        ]
    ],
    "notification-createLark": [
        "POST",
        "/notification.createLark",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "webhookUrl"
        ]
    ],
    "notification-createMattermost": [
        "POST",
        "/notification.createMattermost",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "webhookUrl",
            "channel",
            "username"
        ]
    ],
    "notification-createNtfy": [
        "POST",
        "/notification.createNtfy",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverUrl",
            "topic",
            "accessToken",
            "priority"
        ]
    ],
    "notification-createPushover": [
        "POST",
        "/notification.createPushover",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "userKey",
            "apiToken",
            "priority",
            "retry",
            "expire"
        ]
    ],
    "notification-createResend": [
        "POST",
        "/notification.createResend",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "apiKey",
            "fromAddress",
            "toAddresses"
        ]
    ],
    "notification-createSlack": [
        "POST",
        "/notification.createSlack",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "webhookUrl",
            "channel"
        ]
    ],
    "notification-createTeams": [
        "POST",
        "/notification.createTeams",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "webhookUrl"
        ]
    ],
    "notification-createTelegram": [
        "POST",
        "/notification.createTelegram",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "botToken",
            "chatId",
            "messageThreadId"
        ]
    ],
    "notification-getEmailProviders": [
        "GET",
        "/notification.getEmailProviders",
        [],
        []
    ],
    "notification-one": [
        "GET",
        "/notification.one",
        [],
        [
            "notificationId"
        ]
    ],
    "notification-receiveNotification": [
        "POST",
        "/notification.receiveNotification",
        [],
        [
            "ServerType",
            "Type",
            "Value",
            "Threshold",
            "Message",
            "Timestamp",
            "Token"
        ]
    ],
    "notification-remove": [
        "POST",
        "/notification.remove",
        [],
        [
            "notificationId"
        ]
    ],
    "notification-testCustomConnection": [
        "POST",
        "/notification.testCustomConnection",
        [],
        [
            "endpoint",
            "headers"
        ]
    ],
    "notification-testDiscordConnection": [
        "POST",
        "/notification.testDiscordConnection",
        [],
        [
            "webhookUrl",
            "decoration"
        ]
    ],
    "notification-testEmailConnection": [
        "POST",
        "/notification.testEmailConnection",
        [],
        [
            "smtpServer",
            "smtpPort",
            "username",
            "password",
            "toAddresses",
            "fromAddress"
        ]
    ],
    "notification-testGotifyConnection": [
        "POST",
        "/notification.testGotifyConnection",
        [],
        [
            "serverUrl",
            "appToken",
            "priority",
            "decoration"
        ]
    ],
    "notification-testLarkConnection": [
        "POST",
        "/notification.testLarkConnection",
        [],
        [
            "webhookUrl"
        ]
    ],
    "notification-testMattermostConnection": [
        "POST",
        "/notification.testMattermostConnection",
        [],
        [
            "webhookUrl",
            "channel",
            "username"
        ]
    ],
    "notification-testNtfyConnection": [
        "POST",
        "/notification.testNtfyConnection",
        [],
        [
            "serverUrl",
            "topic",
            "accessToken",
            "priority"
        ]
    ],
    "notification-testPushoverConnection": [
        "POST",
        "/notification.testPushoverConnection",
        [],
        [
            "userKey",
            "apiToken",
            "priority",
            "retry",
            "expire"
        ]
    ],
    "notification-testResendConnection": [
        "POST",
        "/notification.testResendConnection",
        [],
        [
            "apiKey",
            "fromAddress",
            "toAddresses"
        ]
    ],
    "notification-testSlackConnection": [
        "POST",
        "/notification.testSlackConnection",
        [],
        [
            "webhookUrl",
            "channel"
        ]
    ],
    "notification-testTeamsConnection": [
        "POST",
        "/notification.testTeamsConnection",
        [],
        [
            "webhookUrl"
        ]
    ],
    "notification-testTelegramConnection": [
        "POST",
        "/notification.testTelegramConnection",
        [],
        [
            "botToken",
            "chatId",
            "messageThreadId"
        ]
    ],
    "notification-updateCustom": [
        "POST",
        "/notification.updateCustom",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "endpoint",
            "headers",
            "notificationId",
            "customId",
            "organizationId"
        ]
    ],
    "notification-updateDiscord": [
        "POST",
        "/notification.updateDiscord",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "webhookUrl",
            "decoration",
            "notificationId",
            "discordId",
            "organizationId"
        ]
    ],
    "notification-updateEmail": [
        "POST",
        "/notification.updateEmail",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "smtpServer",
            "smtpPort",
            "username",
            "password",
            "fromAddress",
            "toAddresses",
            "notificationId",
            "emailId",
            "organizationId"
        ]
    ],
    "notification-updateGotify": [
        "POST",
        "/notification.updateGotify",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverUrl",
            "appToken",
            "priority",
            "decoration",
            "notificationId",
            "gotifyId",
            "organizationId"
        ]
    ],
    "notification-updateLark": [
        "POST",
        "/notification.updateLark",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "webhookUrl",
            "notificationId",
            "larkId",
            "organizationId"
        ]
    ],
    "notification-updateMattermost": [
        "POST",
        "/notification.updateMattermost",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "webhookUrl",
            "channel",
            "username",
            "notificationId",
            "mattermostId",
            "organizationId"
        ]
    ],
    "notification-updateNtfy": [
        "POST",
        "/notification.updateNtfy",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverUrl",
            "topic",
            "accessToken",
            "priority",
            "notificationId",
            "ntfyId",
            "organizationId"
        ]
    ],
    "notification-updatePushover": [
        "POST",
        "/notification.updatePushover",
        [],
        [
            "notificationId",
            "pushoverId",
            "organizationId",
            "userKey",
            "apiToken",
            "priority",
            "retry",
            "expire",
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold"
        ]
    ],
    "notification-updateResend": [
        "POST",
        "/notification.updateResend",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "apiKey",
            "fromAddress",
            "toAddresses",
            "notificationId",
            "resendId",
            "organizationId"
        ]
    ],
    "notification-updateSlack": [
        "POST",
        "/notification.updateSlack",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "webhookUrl",
            "channel",
            "notificationId",
            "slackId",
            "organizationId"
        ]
    ],
    "notification-updateTeams": [
        "POST",
        "/notification.updateTeams",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "webhookUrl",
            "notificationId",
            "teamsId",
            "organizationId"
        ]
    ],
    "notification-updateTelegram": [
        "POST",
        "/notification.updateTelegram",
        [],
        [
            "appBuildError",
            "databaseBackup",
            "dokployBackup",
            "volumeBackup",
            "dokployRestart",
            "name",
            "appDeploy",
            "dockerCleanup",
            "serverThreshold",
            "botToken",
            "chatId",
            "messageThreadId",
            "notificationId",
            "telegramId",
            "organizationId"
        ]
    ],
    "organization-active": [
        "GET",
        "/organization.active",
        [],
        []
    ],
    "organization-all": [
        "GET",
        "/organization.all",
        [],
        []
    ],
    "organization-allInvitations": [
        "GET",
        "/organization.allInvitations",
        [],
        []
    ],
    "organization-create": [
        "POST",
        "/organization.create",
        [],
        [
            "name",
            "logo"
        ]
    ],
    "organization-delete": [
        "POST",
        "/organization.delete",
        [],
        [
            "organizationId"
        ]
    ],
    "organization-inviteMember": [
        "POST",
        "/organization.inviteMember",
        [],
        [
            "email",
            "role"
        ]
    ],
    "organization-one": [
        "GET",
        "/organization.one",
        [],
        [
            "organizationId"
        ]
    ],
    "organization-removeInvitation": [
        "POST",
        "/organization.removeInvitation",
        [],
        [
            "invitationId"
        ]
    ],
    "organization-setDefault": [
        "POST",
        "/organization.setDefault",
        [],
        [
            "organizationId"
        ]
    ],
    "organization-update": [
        "POST",
        "/organization.update",
        [],
        [
            "organizationId",
            "name",
            "logo"
        ]
    ],
    "organization-updateMemberRole": [
        "POST",
        "/organization.updateMemberRole",
        [],
        [
            "memberId",
            "role"
        ]
    ],
    "patch-byEntityId": [
        "GET",
        "/patch.byEntityId",
        [],
        [
            "id",
            "type"
        ]
    ],
    "patch-cleanPatchRepos": [
        "POST",
        "/patch.cleanPatchRepos",
        [],
        [
            "serverId"
        ]
    ],
    "patch-create": [
        "POST",
        "/patch.create",
        [],
        [
            "filePath",
            "content",
            "type",
            "enabled",
            "applicationId",
            "composeId"
        ]
    ],
    "patch-delete": [
        "POST",
        "/patch.delete",
        [],
        [
            "patchId"
        ]
    ],
    "patch-ensureRepo": [
        "POST",
        "/patch.ensureRepo",
        [],
        [
            "id",
            "type"
        ]
    ],
    "patch-markFileForDeletion": [
        "POST",
        "/patch.markFileForDeletion",
        [],
        [
            "id",
            "type",
            "filePath"
        ]
    ],
    "patch-one": [
        "GET",
        "/patch.one",
        [],
        [
            "patchId"
        ]
    ],
    "patch-readRepoDirectories": [
        "GET",
        "/patch.readRepoDirectories",
        [],
        [
            "id",
            "type",
            "repoPath"
        ]
    ],
    "patch-readRepoFile": [
        "GET",
        "/patch.readRepoFile",
        [],
        [
            "id",
            "type",
            "filePath"
        ]
    ],
    "patch-saveFileAsPatch": [
        "POST",
        "/patch.saveFileAsPatch",
        [],
        [
            "id",
            "type",
            "filePath",
            "content",
            "patchType"
        ]
    ],
    "patch-toggleEnabled": [
        "POST",
        "/patch.toggleEnabled",
        [],
        [
            "patchId",
            "enabled"
        ]
    ],
    "patch-update": [
        "POST",
        "/patch.update",
        [],
        [
            "patchId",
            "type",
            "filePath",
            "enabled",
            "content",
            "createdAt",
            "updatedAt"
        ]
    ],
    "port-create": [
        "POST",
        "/port.create",
        [],
        [
            "publishedPort",
            "publishMode",
            "targetPort",
            "protocol",
            "applicationId"
        ]
    ],
    "port-delete": [
        "POST",
        "/port.delete",
        [],
        [
            "portId"
        ]
    ],
    "port-one": [
        "GET",
        "/port.one",
        [],
        [
            "portId"
        ]
    ],
    "port-update": [
        "POST",
        "/port.update",
        [],
        [
            "portId",
            "publishedPort",
            "publishMode",
            "targetPort",
            "protocol"
        ]
    ],
    "postgres-changePassword": [
        "POST",
        "/postgres.changePassword",
        [],
        [
            "postgresId",
            "password"
        ]
    ],
    "postgres-changeStatus": [
        "POST",
        "/postgres.changeStatus",
        [],
        [
            "postgresId",
            "applicationStatus"
        ]
    ],
    "postgres-create": [
        "POST",
        "/postgres.create",
        [],
        [
            "name",
            "appName",
            "databaseName",
            "databaseUser",
            "databasePassword",
            "dockerImage",
            "environmentId",
            "description",
            "serverId"
        ]
    ],
    "postgres-deploy": [
        "POST",
        "/postgres.deploy",
        [],
        [
            "postgresId"
        ]
    ],
    "postgres-move": [
        "POST",
        "/postgres.move",
        [],
        [
            "postgresId",
            "targetEnvironmentId"
        ]
    ],
    "postgres-one": [
        "GET",
        "/postgres.one",
        [],
        [
            "postgresId"
        ]
    ],
    "postgres-readLogs": [
        "GET",
        "/postgres.readLogs",
        [],
        [
            "postgresId",
            "tail",
            "since",
            "search"
        ]
    ],
    "postgres-rebuild": [
        "POST",
        "/postgres.rebuild",
        [],
        [
            "postgresId"
        ]
    ],
    "postgres-reload": [
        "POST",
        "/postgres.reload",
        [],
        [
            "postgresId",
            "appName"
        ]
    ],
    "postgres-remove": [
        "POST",
        "/postgres.remove",
        [],
        [
            "postgresId"
        ]
    ],
    "postgres-saveEnvironment": [
        "POST",
        "/postgres.saveEnvironment",
        [],
        [
            "postgresId",
            "env"
        ]
    ],
    "postgres-saveExternalPort": [
        "POST",
        "/postgres.saveExternalPort",
        [],
        [
            "postgresId",
            "externalPort"
        ]
    ],
    "postgres-search": [
        "GET",
        "/postgres.search",
        [],
        [
            "q",
            "name",
            "appName",
            "description",
            "projectId",
            "environmentId",
            "limit",
            "offset"
        ]
    ],
    "postgres-start": [
        "POST",
        "/postgres.start",
        [],
        [
            "postgresId"
        ]
    ],
    "postgres-stop": [
        "POST",
        "/postgres.stop",
        [],
        [
            "postgresId"
        ]
    ],
    "postgres-update": [
        "POST",
        "/postgres.update",
        [],
        [
            "postgresId",
            "name",
            "appName",
            "databaseName",
            "databaseUser",
            "databasePassword",
            "description",
            "dockerImage",
            "command",
            "args",
            "env",
            "memoryReservation",
            "externalPort",
            "memoryLimit",
            "cpuReservation",
            "cpuLimit",
            "applicationStatus",
            "healthCheckSwarm",
            "restartPolicySwarm",
            "placementSwarm",
            "updateConfigSwarm",
            "rollbackConfigSwarm",
            "modeSwarm",
            "labelsSwarm",
            "networkSwarm",
            "stopGracePeriodSwarm",
            "endpointSpecSwarm",
            "ulimitsSwarm",
            "replicas",
            "createdAt",
            "environmentId"
        ]
    ],
    "previewDeployment-all": [
        "GET",
        "/previewDeployment.all",
        [],
        [
            "applicationId"
        ]
    ],
    "previewDeployment-delete": [
        "POST",
        "/previewDeployment.delete",
        [],
        [
            "previewDeploymentId"
        ]
    ],
    "previewDeployment-one": [
        "GET",
        "/previewDeployment.one",
        [],
        [
            "previewDeploymentId"
        ]
    ],
    "previewDeployment-redeploy": [
        "POST",
        "/previewDeployment.redeploy",
        [],
        [
            "previewDeploymentId",
            "title",
            "description"
        ]
    ],
    "project-all": [
        "GET",
        "/project.all",
        [],
        []
    ],
    "project-allForPermissions": [
        "GET",
        "/project.allForPermissions",
        [],
        []
    ],
    "project-create": [
        "POST",
        "/project.create",
        [],
        [
            "name",
            "description",
            "env"
        ]
    ],
    "project-duplicate": [
        "POST",
        "/project.duplicate",
        [],
        [
            "sourceEnvironmentId",
            "name",
            "description",
            "includeServices",
            "selectedServices",
            "duplicateInSameProject"
        ]
    ],
    "project-homeStats": [
        "GET",
        "/project.homeStats",
        [],
        []
    ],
    "project-one": [
        "GET",
        "/project.one",
        [],
        [
            "projectId"
        ]
    ],
    "project-remove": [
        "POST",
        "/project.remove",
        [],
        [
            "projectId"
        ]
    ],
    "project-search": [
        "GET",
        "/project.search",
        [],
        [
            "q",
            "name",
            "description",
            "limit",
            "offset"
        ]
    ],
    "project-update": [
        "POST",
        "/project.update",
        [],
        [
            "projectId",
            "name",
            "description",
            "createdAt",
            "organizationId",
            "env"
        ]
    ],
    "redirects-create": [
        "POST",
        "/redirects.create",
        [],
        [
            "regex",
            "replacement",
            "permanent",
            "applicationId"
        ]
    ],
    "redirects-delete": [
        "POST",
        "/redirects.delete",
        [],
        [
            "redirectId"
        ]
    ],
    "redirects-one": [
        "GET",
        "/redirects.one",
        [],
        [
            "redirectId"
        ]
    ],
    "redirects-update": [
        "POST",
        "/redirects.update",
        [],
        [
            "redirectId",
            "regex",
            "replacement",
            "permanent"
        ]
    ],
    "redis-changePassword": [
        "POST",
        "/redis.changePassword",
        [],
        [
            "redisId",
            "password"
        ]
    ],
    "redis-changeStatus": [
        "POST",
        "/redis.changeStatus",
        [],
        [
            "redisId",
            "applicationStatus"
        ]
    ],
    "redis-create": [
        "POST",
        "/redis.create",
        [],
        [
            "name",
            "appName",
            "databasePassword",
            "dockerImage",
            "environmentId",
            "description",
            "serverId"
        ]
    ],
    "redis-deploy": [
        "POST",
        "/redis.deploy",
        [],
        [
            "redisId"
        ]
    ],
    "redis-move": [
        "POST",
        "/redis.move",
        [],
        [
            "redisId",
            "targetEnvironmentId"
        ]
    ],
    "redis-one": [
        "GET",
        "/redis.one",
        [],
        [
            "redisId"
        ]
    ],
    "redis-readLogs": [
        "GET",
        "/redis.readLogs",
        [],
        [
            "redisId",
            "tail",
            "since",
            "search"
        ]
    ],
    "redis-rebuild": [
        "POST",
        "/redis.rebuild",
        [],
        [
            "redisId"
        ]
    ],
    "redis-reload": [
        "POST",
        "/redis.reload",
        [],
        [
            "redisId",
            "appName"
        ]
    ],
    "redis-remove": [
        "POST",
        "/redis.remove",
        [],
        [
            "redisId"
        ]
    ],
    "redis-saveEnvironment": [
        "POST",
        "/redis.saveEnvironment",
        [],
        [
            "redisId",
            "env"
        ]
    ],
    "redis-saveExternalPort": [
        "POST",
        "/redis.saveExternalPort",
        [],
        [
            "redisId",
            "externalPort"
        ]
    ],
    "redis-search": [
        "GET",
        "/redis.search",
        [],
        [
            "q",
            "name",
            "appName",
            "description",
            "projectId",
            "environmentId",
            "limit",
            "offset"
        ]
    ],
    "redis-start": [
        "POST",
        "/redis.start",
        [],
        [
            "redisId"
        ]
    ],
    "redis-stop": [
        "POST",
        "/redis.stop",
        [],
        [
            "redisId"
        ]
    ],
    "redis-update": [
        "POST",
        "/redis.update",
        [],
        [
            "redisId",
            "name",
            "appName",
            "description",
            "databasePassword",
            "dockerImage",
            "command",
            "args",
            "env",
            "memoryReservation",
            "memoryLimit",
            "cpuReservation",
            "cpuLimit",
            "externalPort",
            "createdAt",
            "applicationStatus",
            "healthCheckSwarm",
            "restartPolicySwarm",
            "placementSwarm",
            "updateConfigSwarm",
            "rollbackConfigSwarm",
            "modeSwarm",
            "labelsSwarm",
            "networkSwarm",
            "stopGracePeriodSwarm",
            "endpointSpecSwarm",
            "ulimitsSwarm",
            "replicas",
            "environmentId"
        ]
    ],
    "registry-all": [
        "GET",
        "/registry.all",
        [],
        []
    ],
    "registry-create": [
        "POST",
        "/registry.create",
        [],
        [
            "registryName",
            "username",
            "password",
            "registryUrl",
            "registryType",
            "imagePrefix",
            "serverId"
        ]
    ],
    "registry-one": [
        "GET",
        "/registry.one",
        [],
        [
            "registryId"
        ]
    ],
    "registry-remove": [
        "POST",
        "/registry.remove",
        [],
        [
            "registryId"
        ]
    ],
    "registry-testRegistry": [
        "POST",
        "/registry.testRegistry",
        [],
        [
            "registryName",
            "username",
            "password",
            "registryUrl",
            "registryType",
            "imagePrefix",
            "serverId"
        ]
    ],
    "registry-testRegistryById": [
        "POST",
        "/registry.testRegistryById",
        [],
        [
            "registryId",
            "serverId"
        ]
    ],
    "registry-update": [
        "POST",
        "/registry.update",
        [],
        [
            "registryId",
            "registryName",
            "imagePrefix",
            "username",
            "password",
            "registryUrl",
            "createdAt",
            "registryType",
            "organizationId",
            "serverId"
        ]
    ],
    "rollback-delete": [
        "POST",
        "/rollback.delete",
        [],
        [
            "rollbackId"
        ]
    ],
    "rollback-rollback": [
        "POST",
        "/rollback.rollback",
        [],
        [
            "rollbackId"
        ]
    ],
    "schedule-create": [
        "POST",
        "/schedule.create",
        [],
        [
            "scheduleId",
            "name",
            "cronExpression",
            "appName",
            "serviceName",
            "shellType",
            "scheduleType",
            "command",
            "script",
            "applicationId",
            "composeId",
            "serverId",
            "userId",
            "enabled",
            "timezone",
            "createdAt"
        ]
    ],
    "schedule-delete": [
        "POST",
        "/schedule.delete",
        [],
        [
            "scheduleId"
        ]
    ],
    "schedule-list": [
        "GET",
        "/schedule.list",
        [],
        [
            "id",
            "scheduleType"
        ]
    ],
    "schedule-one": [
        "GET",
        "/schedule.one",
        [],
        [
            "scheduleId"
        ]
    ],
    "schedule-runManually": [
        "POST",
        "/schedule.runManually",
        [],
        [
            "scheduleId"
        ]
    ],
    "schedule-update": [
        "POST",
        "/schedule.update",
        [],
        [
            "scheduleId",
            "name",
            "cronExpression",
            "appName",
            "serviceName",
            "shellType",
            "scheduleType",
            "command",
            "script",
            "applicationId",
            "composeId",
            "serverId",
            "userId",
            "enabled",
            "timezone",
            "createdAt"
        ]
    ],
    "security-create": [
        "POST",
        "/security.create",
        [],
        [
            "applicationId",
            "username",
            "password"
        ]
    ],
    "security-delete": [
        "POST",
        "/security.delete",
        [],
        [
            "securityId"
        ]
    ],
    "security-one": [
        "GET",
        "/security.one",
        [],
        [
            "securityId"
        ]
    ],
    "security-update": [
        "POST",
        "/security.update",
        [],
        [
            "securityId",
            "username",
            "password"
        ]
    ],
    "server-all": [
        "GET",
        "/server.all",
        [],
        []
    ],
    "server-allForPermissions": [
        "GET",
        "/server.allForPermissions",
        [],
        []
    ],
    "server-buildServers": [
        "GET",
        "/server.buildServers",
        [],
        []
    ],
    "server-count": [
        "GET",
        "/server.count",
        [],
        []
    ],
    "server-create": [
        "POST",
        "/server.create",
        [],
        [
            "name",
            "description",
            "ipAddress",
            "port",
            "username",
            "sshKeyId",
            "serverType"
        ]
    ],
    "server-getDefaultCommand": [
        "GET",
        "/server.getDefaultCommand",
        [],
        [
            "serverId"
        ]
    ],
    "server-getServerMetrics": [
        "GET",
        "/server.getServerMetrics",
        [],
        [
            "url",
            "token",
            "dataPoints"
        ]
    ],
    "server-getServerTime": [
        "GET",
        "/server.getServerTime",
        [],
        []
    ],
    "server-one": [
        "GET",
        "/server.one",
        [],
        [
            "serverId"
        ]
    ],
    "server-publicIp": [
        "GET",
        "/server.publicIp",
        [],
        []
    ],
    "server-remove": [
        "POST",
        "/server.remove",
        [],
        [
            "serverId"
        ]
    ],
    "server-security": [
        "GET",
        "/server.security",
        [],
        [
            "serverId"
        ]
    ],
    "server-setup": [
        "POST",
        "/server.setup",
        [],
        [
            "serverId"
        ]
    ],
    "server-setupMonitoring": [
        "POST",
        "/server.setupMonitoring",
        [],
        [
            "serverId",
            "metricsConfig"
        ]
    ],
    "server-update": [
        "POST",
        "/server.update",
        [],
        [
            "name",
            "description",
            "serverId",
            "ipAddress",
            "port",
            "username",
            "sshKeyId",
            "serverType",
            "command"
        ]
    ],
    "server-validate": [
        "GET",
        "/server.validate",
        [],
        [
            "serverId"
        ]
    ],
    "server-withSSHKey": [
        "GET",
        "/server.withSSHKey",
        [],
        []
    ],
    "settings-assignDomainServer": [
        "POST",
        "/settings.assignDomainServer",
        [],
        [
            "host",
            "certificateType",
            "letsEncryptEmail",
            "https"
        ]
    ],
    "settings-checkGPUStatus": [
        "GET",
        "/settings.checkGPUStatus",
        [],
        [
            "serverId"
        ]
    ],
    "settings-checkInfrastructureHealth": [
        "GET",
        "/settings.checkInfrastructureHealth",
        [],
        []
    ],
    "settings-cleanAll": [
        "POST",
        "/settings.cleanAll",
        [],
        [
            "serverId"
        ]
    ],
    "settings-cleanAllDeploymentQueue": [
        "POST",
        "/settings.cleanAllDeploymentQueue",
        [],
        []
    ],
    "settings-cleanDockerBuilder": [
        "POST",
        "/settings.cleanDockerBuilder",
        [],
        [
            "serverId"
        ]
    ],
    "settings-cleanDockerPrune": [
        "POST",
        "/settings.cleanDockerPrune",
        [],
        [
            "serverId"
        ]
    ],
    "settings-cleanMonitoring": [
        "POST",
        "/settings.cleanMonitoring",
        [],
        []
    ],
    "settings-cleanRedis": [
        "POST",
        "/settings.cleanRedis",
        [],
        []
    ],
    "settings-cleanSSHPrivateKey": [
        "POST",
        "/settings.cleanSSHPrivateKey",
        [],
        []
    ],
    "settings-cleanStoppedContainers": [
        "POST",
        "/settings.cleanStoppedContainers",
        [],
        [
            "serverId"
        ]
    ],
    "settings-cleanUnusedImages": [
        "POST",
        "/settings.cleanUnusedImages",
        [],
        [
            "serverId"
        ]
    ],
    "settings-cleanUnusedVolumes": [
        "POST",
        "/settings.cleanUnusedVolumes",
        [],
        [
            "serverId"
        ]
    ],
    "settings-getDockerDiskUsage": [
        "GET",
        "/settings.getDockerDiskUsage",
        [],
        []
    ],
    "settings-getDokployCloudIps": [
        "GET",
        "/settings.getDokployCloudIps",
        [],
        []
    ],
    "settings-getDokployVersion": [
        "GET",
        "/settings.getDokployVersion",
        [],
        []
    ],
    "settings-getIp": [
        "GET",
        "/settings.getIp",
        [],
        []
    ],
    "settings-getLogCleanupStatus": [
        "GET",
        "/settings.getLogCleanupStatus",
        [],
        []
    ],
    "settings-getOpenApiDocument": [
        "GET",
        "/settings.getOpenApiDocument",
        [],
        []
    ],
    "settings-getReleaseTag": [
        "GET",
        "/settings.getReleaseTag",
        [],
        []
    ],
    "settings-getTraefikPorts": [
        "GET",
        "/settings.getTraefikPorts",
        [],
        [
            "serverId"
        ]
    ],
    "settings-getUpdateData": [
        "POST",
        "/settings.getUpdateData",
        [],
        []
    ],
    "settings-getWebServerSettings": [
        "GET",
        "/settings.getWebServerSettings",
        [],
        []
    ],
    "settings-haveActivateRequests": [
        "GET",
        "/settings.haveActivateRequests",
        [],
        []
    ],
    "settings-haveTraefikDashboardPortEnabled": [
        "GET",
        "/settings.haveTraefikDashboardPortEnabled",
        [],
        [
            "serverId"
        ]
    ],
    "settings-health": [
        "GET",
        "/settings.health",
        [],
        []
    ],
    "settings-isCloud": [
        "GET",
        "/settings.isCloud",
        [],
        []
    ],
    "settings-isUserSubscribed": [
        "GET",
        "/settings.isUserSubscribed",
        [],
        []
    ],
    "settings-readDirectories": [
        "GET",
        "/settings.readDirectories",
        [],
        [
            "serverId"
        ]
    ],
    "settings-readMiddlewareTraefikConfig": [
        "GET",
        "/settings.readMiddlewareTraefikConfig",
        [],
        []
    ],
    "settings-readTraefikConfig": [
        "GET",
        "/settings.readTraefikConfig",
        [],
        []
    ],
    "settings-readTraefikEnv": [
        "GET",
        "/settings.readTraefikEnv",
        [],
        [
            "serverId"
        ]
    ],
    "settings-readTraefikFile": [
        "GET",
        "/settings.readTraefikFile",
        [],
        [
            "path",
            "serverId"
        ]
    ],
    "settings-readWebServerTraefikConfig": [
        "GET",
        "/settings.readWebServerTraefikConfig",
        [],
        []
    ],
    "settings-reloadRedis": [
        "POST",
        "/settings.reloadRedis",
        [],
        []
    ],
    "settings-reloadServer": [
        "POST",
        "/settings.reloadServer",
        [],
        []
    ],
    "settings-reloadTraefik": [
        "POST",
        "/settings.reloadTraefik",
        [],
        [
            "serverId"
        ]
    ],
    "settings-saveSSHPrivateKey": [
        "POST",
        "/settings.saveSSHPrivateKey",
        [],
        [
            "sshPrivateKey"
        ]
    ],
    "settings-setupGPU": [
        "POST",
        "/settings.setupGPU",
        [],
        [
            "serverId"
        ]
    ],
    "settings-toggleDashboard": [
        "POST",
        "/settings.toggleDashboard",
        [],
        [
            "enableDashboard",
            "serverId"
        ]
    ],
    "settings-toggleRequests": [
        "POST",
        "/settings.toggleRequests",
        [],
        [
            "enable"
        ]
    ],
    "settings-updateDockerCleanup": [
        "POST",
        "/settings.updateDockerCleanup",
        [],
        [
            "enableDockerCleanup",
            "serverId"
        ]
    ],
    "settings-updateLogCleanup": [
        "POST",
        "/settings.updateLogCleanup",
        [],
        [
            "cronExpression"
        ]
    ],
    "settings-updateMiddlewareTraefikConfig": [
        "POST",
        "/settings.updateMiddlewareTraefikConfig",
        [],
        [
            "traefikConfig"
        ]
    ],
    "settings-updateServer": [
        "POST",
        "/settings.updateServer",
        [],
        []
    ],
    "settings-updateServerIp": [
        "POST",
        "/settings.updateServerIp",
        [],
        [
            "serverIp"
        ]
    ],
    "settings-updateTraefikConfig": [
        "POST",
        "/settings.updateTraefikConfig",
        [],
        [
            "traefikConfig"
        ]
    ],
    "settings-updateTraefikFile": [
        "POST",
        "/settings.updateTraefikFile",
        [],
        [
            "path",
            "traefikConfig",
            "serverId"
        ]
    ],
    "settings-updateTraefikPorts": [
        "POST",
        "/settings.updateTraefikPorts",
        [],
        [
            "serverId",
            "additionalPorts"
        ]
    ],
    "settings-updateWebServerTraefikConfig": [
        "POST",
        "/settings.updateWebServerTraefikConfig",
        [],
        [
            "traefikConfig"
        ]
    ],
    "settings-writeTraefikEnv": [
        "POST",
        "/settings.writeTraefikEnv",
        [],
        [
            "env",
            "serverId"
        ]
    ],
    "sshKey-all": [
        "GET",
        "/sshKey.all",
        [],
        []
    ],
    "sshKey-allForApps": [
        "GET",
        "/sshKey.allForApps",
        [],
        []
    ],
    "sshKey-create": [
        "POST",
        "/sshKey.create",
        [],
        [
            "name",
            "description",
            "privateKey",
            "publicKey",
            "organizationId"
        ]
    ],
    "sshKey-generate": [
        "POST",
        "/sshKey.generate",
        [],
        [
            "type"
        ]
    ],
    "sshKey-one": [
        "GET",
        "/sshKey.one",
        [],
        [
            "sshKeyId"
        ]
    ],
    "sshKey-remove": [
        "POST",
        "/sshKey.remove",
        [],
        [
            "sshKeyId"
        ]
    ],
    "sshKey-update": [
        "POST",
        "/sshKey.update",
        [],
        [
            "name",
            "description",
            "lastUsedAt",
            "sshKeyId"
        ]
    ],
    "sso-addTrustedOrigin": [
        "POST",
        "/sso.addTrustedOrigin",
        [],
        [
            "origin"
        ]
    ],
    "sso-deleteProvider": [
        "POST",
        "/sso.deleteProvider",
        [],
        [
            "providerId"
        ]
    ],
    "sso-getTrustedOrigins": [
        "GET",
        "/sso.getTrustedOrigins",
        [],
        []
    ],
    "sso-listProviders": [
        "GET",
        "/sso.listProviders",
        [],
        []
    ],
    "sso-one": [
        "GET",
        "/sso.one",
        [],
        [
            "providerId"
        ]
    ],
    "sso-register": [
        "POST",
        "/sso.register",
        [],
        [
            "providerId",
            "issuer",
            "domains",
            "oidcConfig",
            "samlConfig",
            "organizationId",
            "overrideUserInfo"
        ]
    ],
    "sso-removeTrustedOrigin": [
        "POST",
        "/sso.removeTrustedOrigin",
        [],
        [
            "origin"
        ]
    ],
    "sso-showSignInWithSSO": [
        "GET",
        "/sso.showSignInWithSSO",
        [],
        []
    ],
    "sso-update": [
        "POST",
        "/sso.update",
        [],
        [
            "providerId",
            "issuer",
            "domains",
            "oidcConfig",
            "samlConfig",
            "organizationId",
            "overrideUserInfo"
        ]
    ],
    "sso-updateTrustedOrigin": [
        "POST",
        "/sso.updateTrustedOrigin",
        [],
        [
            "oldOrigin",
            "newOrigin"
        ]
    ],
    "stripe-canCreateMoreServers": [
        "GET",
        "/stripe.canCreateMoreServers",
        [],
        []
    ],
    "stripe-createCheckoutSession": [
        "POST",
        "/stripe.createCheckoutSession",
        [],
        [
            "tier",
            "productId",
            "serverQuantity",
            "isAnnual"
        ]
    ],
    "stripe-createCustomerPortalSession": [
        "POST",
        "/stripe.createCustomerPortalSession",
        [],
        []
    ],
    "stripe-getCurrentPlan": [
        "GET",
        "/stripe.getCurrentPlan",
        [],
        []
    ],
    "stripe-getInvoices": [
        "GET",
        "/stripe.getInvoices",
        [],
        []
    ],
    "stripe-getProducts": [
        "GET",
        "/stripe.getProducts",
        [],
        []
    ],
    "stripe-updateInvoiceNotifications": [
        "POST",
        "/stripe.updateInvoiceNotifications",
        [],
        [
            "enabled"
        ]
    ],
    "stripe-upgradeSubscription": [
        "POST",
        "/stripe.upgradeSubscription",
        [],
        [
            "tier",
            "serverQuantity",
            "isAnnual"
        ]
    ],
    "swarm-getContainerStats": [
        "GET",
        "/swarm.getContainerStats",
        [],
        [
            "serverId"
        ]
    ],
    "swarm-getNodeApps": [
        "GET",
        "/swarm.getNodeApps",
        [],
        [
            "serverId"
        ]
    ],
    "swarm-getNodeInfo": [
        "GET",
        "/swarm.getNodeInfo",
        [],
        [
            "nodeId",
            "serverId"
        ]
    ],
    "swarm-getNodes": [
        "GET",
        "/swarm.getNodes",
        [],
        [
            "serverId"
        ]
    ],
    "tag-all": [
        "GET",
        "/tag.all",
        [],
        []
    ],
    "tag-assignToProject": [
        "POST",
        "/tag.assignToProject",
        [],
        [
            "projectId",
            "tagId"
        ]
    ],
    "tag-bulkAssign": [
        "POST",
        "/tag.bulkAssign",
        [],
        [
            "projectId",
            "tagIds"
        ]
    ],
    "tag-create": [
        "POST",
        "/tag.create",
        [],
        [
            "name",
            "color"
        ]
    ],
    "tag-one": [
        "GET",
        "/tag.one",
        [],
        [
            "tagId"
        ]
    ],
    "tag-remove": [
        "POST",
        "/tag.remove",
        [],
        [
            "tagId"
        ]
    ],
    "tag-removeFromProject": [
        "POST",
        "/tag.removeFromProject",
        [],
        [
            "projectId",
            "tagId"
        ]
    ],
    "tag-update": [
        "POST",
        "/tag.update",
        [],
        [
            "tagId",
            "name",
            "color",
            "createdAt",
            "organizationId"
        ]
    ],
    "user-all": [
        "GET",
        "/user.all",
        [],
        []
    ],
    "user-assignPermissions": [
        "POST",
        "/user.assignPermissions",
        [],
        [
            "id",
            "accessedProjects",
            "accessedEnvironments",
            "accessedServices",
            "accessedGitProviders",
            "accessedServers",
            "canCreateProjects",
            "canCreateServices",
            "canDeleteProjects",
            "canDeleteServices",
            "canAccessToDocker",
            "canAccessToTraefikFiles",
            "canAccessToAPI",
            "canAccessToSSHKeys",
            "canAccessToGitProviders",
            "canDeleteEnvironments",
            "canCreateEnvironments"
        ]
    ],
    "user-checkUserOrganizations": [
        "GET",
        "/user.checkUserOrganizations",
        [],
        [
            "userId"
        ]
    ],
    "user-createApiKey": [
        "POST",
        "/user.createApiKey",
        [],
        [
            "name",
            "prefix",
            "expiresIn",
            "metadata",
            "rateLimitEnabled",
            "rateLimitTimeWindow",
            "rateLimitMax",
            "remaining",
            "refillAmount",
            "refillInterval"
        ]
    ],
    "user-createUserWithCredentials": [
        "POST",
        "/user.createUserWithCredentials",
        [],
        [
            "email",
            "password",
            "role"
        ]
    ],
    "user-deleteApiKey": [
        "POST",
        "/user.deleteApiKey",
        [],
        [
            "apiKeyId"
        ]
    ],
    "user-generateToken": [
        "POST",
        "/user.generateToken",
        [],
        []
    ],
    "user-get": [
        "GET",
        "/user.get",
        [],
        []
    ],
    "user-getBackups": [
        "GET",
        "/user.getBackups",
        [],
        []
    ],
    "user-getBookmarkedTemplates": [
        "GET",
        "/user.getBookmarkedTemplates",
        [],
        []
    ],
    "user-getContainerMetrics": [
        "GET",
        "/user.getContainerMetrics",
        [],
        [
            "url",
            "token",
            "appName",
            "dataPoints"
        ]
    ],
    "user-getInvitations": [
        "GET",
        "/user.getInvitations",
        [],
        []
    ],
    "user-getMetricsToken": [
        "GET",
        "/user.getMetricsToken",
        [],
        []
    ],
    "user-getPermissions": [
        "GET",
        "/user.getPermissions",
        [],
        []
    ],
    "user-getServerMetrics": [
        "GET",
        "/user.getServerMetrics",
        [],
        []
    ],
    "user-getUserByToken": [
        "GET",
        "/user.getUserByToken",
        [],
        [
            "token"
        ]
    ],
    "user-haveRootAccess": [
        "GET",
        "/user.haveRootAccess",
        [],
        []
    ],
    "user-one": [
        "GET",
        "/user.one",
        [],
        [
            "userId"
        ]
    ],
    "user-remove": [
        "POST",
        "/user.remove",
        [],
        [
            "userId"
        ]
    ],
    "user-sendInvitation": [
        "POST",
        "/user.sendInvitation",
        [],
        [
            "invitationId",
            "notificationId"
        ]
    ],
    "user-session": [
        "GET",
        "/user.session",
        [],
        []
    ],
    "user-toggleTemplateBookmark": [
        "POST",
        "/user.toggleTemplateBookmark",
        [],
        [
            "templateId"
        ]
    ],
    "user-update": [
        "POST",
        "/user.update",
        [],
        [
            "id",
            "firstName",
            "lastName",
            "isRegistered",
            "expirationDate",
            "createdAt2",
            "createdAt",
            "twoFactorEnabled",
            "email",
            "emailVerified",
            "image",
            "banned",
            "banReason",
            "banExpires",
            "updatedAt",
            "enablePaidFeatures",
            "allowImpersonation",
            "enableEnterpriseFeatures",
            "licenseKey",
            "stripeCustomerId",
            "stripeSubscriptionId",
            "serversQuantity",
            "sendInvoiceNotifications",
            "password",
            "currentPassword"
        ]
    ],
    "volumeBackups-create": [
        "POST",
        "/volumeBackups.create",
        [],
        [
            "name",
            "volumeName",
            "prefix",
            "serviceType",
            "appName",
            "serviceName",
            "turnOff",
            "cronExpression",
            "keepLatestCount",
            "enabled",
            "applicationId",
            "postgresId",
            "mariadbId",
            "mongoId",
            "mysqlId",
            "redisId",
            "libsqlId",
            "composeId",
            "createdAt",
            "destinationId"
        ]
    ],
    "volumeBackups-delete": [
        "POST",
        "/volumeBackups.delete",
        [],
        [
            "volumeBackupId"
        ]
    ],
    "volumeBackups-list": [
        "GET",
        "/volumeBackups.list",
        [],
        [
            "id",
            "volumeBackupType"
        ]
    ],
    "volumeBackups-one": [
        "GET",
        "/volumeBackups.one",
        [],
        [
            "volumeBackupId"
        ]
    ],
    "volumeBackups-runManually": [
        "POST",
        "/volumeBackups.runManually",
        [],
        [
            "volumeBackupId"
        ]
    ],
    "volumeBackups-update": [
        "POST",
        "/volumeBackups.update",
        [],
        [
            "name",
            "volumeName",
            "prefix",
            "serviceType",
            "appName",
            "serviceName",
            "turnOff",
            "cronExpression",
            "keepLatestCount",
            "enabled",
            "applicationId",
            "postgresId",
            "mariadbId",
            "mongoId",
            "mysqlId",
            "redisId",
            "libsqlId",
            "composeId",
            "createdAt",
            "destinationId",
            "volumeBackupId"
        ]
    ],
    "whitelabeling-get": [
        "GET",
        "/whitelabeling.get",
        [],
        []
    ],
    "whitelabeling-getPublic": [
        "GET",
        "/whitelabeling.getPublic",
        [],
        []
    ],
    "whitelabeling-reset": [
        "POST",
        "/whitelabeling.reset",
        [],
        []
    ],
    "whitelabeling-update": [
        "POST",
        "/whitelabeling.update",
        [],
        [
            "whitelabelingConfig"
        ]
    ]
}

class DokployDynamicAction(Action):
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

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("message") or data.get("error") or data.get("error_summary") or resp.text
            raise ValueError(f"Dokploy API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class DokployProvider(Provider):
    def __init__(self):
        super().__init__(
            service="dokploy",
            display_name="Dokploy",
            category="Developer Tools",
            auth_types=["api_key"],
            description="Dokploy PaaS application deployments, servers, docker containers, and monitoring with 524 actions."
        )
        for act in get_provider_actions("dokploy"):
            self.register_action(DokployDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "{instanceUrl}/api/project.search"
        for key in ["instanceUrl", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))
        if val_url.startswith("{instanceUrl}"):
            inst = str(cred.get("instanceUrl") or cred.get("host") or cred.get("url") or "https://example.com").strip()
            val_url = val_url.replace("{instanceUrl}", inst)

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
            raise ValueError(f"Dokploy connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Dokploy credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Dokploy validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Dokploy Account"
        }
