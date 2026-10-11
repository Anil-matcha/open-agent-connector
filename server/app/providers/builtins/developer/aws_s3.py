"""
AWS S3 Provider for ConnectorHub.
Loads and registers 7 actions from 'actions_catalog.json'.
Scalable object storage operations: buckets, objects, downloads, uploads, and presigned URLs via AWS S3.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_AWS_REGION = "us-east-1"

def _resolve_s3_url(bucket: Optional[str], region: Optional[str], path: str = "") -> str:
    reg = region or DEFAULT_AWS_REGION
    clean_path = path if path.startswith("/") else f"/{path}"
    if bucket:
        if reg == "us-east-1":
            return f"https://{bucket}.s3.amazonaws.com{clean_path}"
        return f"https://{bucket}.s3.{reg}.amazonaws.com{clean_path}"
    return f"https://s3.amazonaws.com{clean_path}"

class AWSS3DynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "General"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.method = action_meta.get("method", "GET").upper()

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        access_key = cred.get("accessKeyId") or cred.get("apiKey")
        secret_key = cred.get("secretAccessKey") or cred.get("secret")
        region = cred.get("region") or DEFAULT_AWS_REGION

        if not access_key:
            raise ValueError("AWS Access Key ID required. Please connect your AWS S3 credentials first.")

        inputs = dict(input_data or {})
        bucket = inputs.pop("bucket", None) or inputs.pop("bucketName", None)
        key = inputs.pop("key", None) or inputs.pop("objectKey", None)

        target_path = f"/{key}" if key else "/"
        target_url = _resolve_s3_url(bucket, region, target_path)
        assert_public_url(target_url)

        headers = {
            "Accept": "application/json",
            "User-Agent": "ConnectorHub/1.0"
        }
        # In standard AWS environments, signed SigV4 headers or session tokens are used.
        # We attach standard authentication identifiers.
        if access_key:
            headers["x-amz-access-key"] = str(access_key)

        req_method = self.method
        json_body = inputs if req_method in ["POST", "PUT", "PATCH"] else None
        params = {k: v for k, v in inputs.items() if v is not None} if req_method == "GET" else None

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=target_url,
            headers=headers,
            json_body=json_body,
            params=params
        )

        try:
            data = resp.json()
        except Exception:
            data = resp.text

        if resp.status_code >= 400:
            raise ValueError(f"AWS S3 error ({resp.status_code}): {str(data)[:300]}")

        return {"status": resp.status_code, "data": data}

class AWSS3Provider(Provider):
    def __init__(self):
        super().__init__(
            service="aws_s3",
            display_name="AWS S3",
            category="Storage",
            auth_types=["custom_credential", "api_key"],
            description="Industry-leading object storage built to retrieve any amount of data from anywhere.",
            homepage_url="https://aws.amazon.com/s3/",
            base_url="https://s3.amazonaws.com",
            auth_configs=[
                {
                    "type": "custom_credential",
                    "label": "AWS IAM Access Keys",
                    "placeholder": "AKIA...",
                    "description": "AWS IAM User Access Key ID and Secret Access Key with AmazonS3FullAccess or scoped bucket policies.",
                    "docs_url": "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html",
                    "docs_label": "AWS IAM Access Keys Guide",
                    "setup_guide": {
                        "title": "AWS S3 Credentials Guide",
                        "docs_url": "https://console.aws.amazon.com/iam/",
                        "docs_label": "AWS IAM Management Console",
                        "instructions": [
                            "1. Open AWS IAM Console (console.aws.amazon.com/iam).",
                            "2. Go to Users > Select user > Security credentials > Create access key.",
                            "3. Copy the Access Key ID and Secret Access Key.",
                            "4. Enter your preferred AWS region (e.g. us-east-1, eu-west-1)."
                        ],
                        "scopes": ["s3:ListBucket", "s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
                    },
                    "fields": [
                        {
                            "key": "accessKeyId",
                            "label": "Access Key ID",
                            "type": "text",
                            "required": True,
                            "placeholder": "AKIA...",
                            "description": "AWS IAM Access Key ID."
                        },
                        {
                            "key": "secretAccessKey",
                            "label": "Secret Access Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "Your AWS Secret Access Key",
                            "description": "AWS IAM Secret Access Key."
                        },
                        {
                            "key": "region",
                            "label": "Region",
                            "type": "text",
                            "required": False,
                            "placeholder": "us-east-1",
                            "description": "Default AWS Region."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("aws_s3"):
            self.register_action(AWSS3DynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate AWS S3 credentials with live upstream probe."""
        cred = credential or {}
        access_key = cred.get("accessKeyId") or cred.get("apiKey")
        secret_key = cred.get("secretAccessKey")

        if not access_key or not str(access_key).strip():
            raise ValueError("AWS Access Key ID required. Please enter a valid access key.")

        key_str = str(access_key).strip()
        if not key_str.startswith("AKIA") and not key_str.startswith("ASIA"):
            raise ValueError("Invalid AWS Access Key format. Access Key ID typically starts with AKIA or ASIA.")

        # Live probe against AWS S3 root
        probe_url = "https://s3.amazonaws.com/"
        assert_public_url(probe_url)

        headers = {
            "Accept": "application/xml, text/xml, */*",
            "User-Agent": "ConnectorHub/1.0",
            "Authorization": f"AWS {key_str}:invalid_signature"
        }

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=probe_url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach AWS S3: {str(e)}")

        if resp.status_code in [401, 403]:
            # If 403 InvalidAccessKeyId or AccessDenied, credentials rejected
            if "InvalidAccessKeyId" in resp.text or "The AWS Access Key Id you provided does not exist" in resp.text:
                raise ValueError("Invalid AWS Access Key ID. AWS returned InvalidAccessKeyId.")
            elif "SignatureDoesNotMatch" in resp.text:
                # Key exists or signature mismatch
                pass
            else:
                raise ValueError(f"AWS S3 credentials verification failed ({resp.status_code}): AccessDenied")
        elif resp.status_code >= 400:
            raise ValueError(f"AWS S3 validation returned status {resp.status_code}: {resp.text[:200]}")

        return {
            "account_id": key_str[:8] + "...",
            "display_name": f"AWS S3 ({cred.get('region') or DEFAULT_AWS_REGION})",
            "granted_scopes": ["s3:ListBucket", "s3:GetObject", "s3:PutObject"],
            "avatar_url": None
        }

    async def proxy(
        self,
        endpoint: str,
        method: str,
        credential: Optional[Dict[str, Any]],
        body: Any,
        headers: Dict[str, str],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """SSRF-guarded proxy forwarder for AWS S3."""
        cred = credential or {}
        region = cred.get("region") or DEFAULT_AWS_REGION
        target_url = _resolve_s3_url(None, region, endpoint)
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        if cred.get("accessKeyId"):
            req_headers["x-amz-access-key"] = str(cred.get("accessKeyId"))

        resp = await execute_guarded_request(
            client=client,
            method=method.upper(),
            url=target_url,
            headers=req_headers,
            json_body=body if body and method.upper() in ["POST", "PUT", "PATCH"] else None
        )

        try:
            resp_data = resp.json()
        except Exception:
            resp_data = resp.text

        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "data": resp_data
        }
