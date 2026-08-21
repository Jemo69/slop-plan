import httpx
from plan_cli.config import get_api_key, get_api_url


class PlanAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API Error {status_code}: {detail}")


class PlanConnectionError(Exception):
    def __init__(self, base_url: str):
        self.base_url = base_url
        super().__init__(f"Cannot connect to {base_url}")


def _get_error_detail(response: httpx.Response) -> str:
    try:
        j = response.json()
        if isinstance(j, dict):
            return j.get("detail", str(j))
        return str(j)
    except Exception:
        return response.text or "Unknown error"


class PlanAPI:
    def __init__(self):
        self.base_url = get_api_url()
        self.api_key = get_api_key()

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _check_auth(self):
        if not self.api_key:
            raise PlanAPIError(401, "Not authenticated. Run 'plan auth init' or 'plan auth login' first.")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=30.0)

    async def register(self, email: str, password: str) -> dict:
        try:
            async with self._client() as client:
                response = await client.post(
                    f"{self.base_url}/api/auth/register",
                    json={"email": email, "password": password},
                )
                if response.status_code != 201:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def login(self, email: str, password: str) -> dict:
        try:
            async with self._client() as client:
                response = await client.post(
                    f"{self.base_url}/api/auth/login",
                    json={"email": email, "password": password},
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def list_projects(self) -> list:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.get(
                    f"{self.base_url}/api/projects",
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json().get("projects", [])
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def get_project(self, project_id: str) -> dict:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.get(
                    f"{self.base_url}/api/projects/{project_id}",
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def create_project(self, name: str, description: str = None) -> dict:
        self._check_auth()
        try:
            async with self._client() as client:
                payload = {"name": name}
                if description:
                    payload["description"] = description
                response = await client.post(
                    f"{self.base_url}/api/projects",
                    json=payload,
                    headers=self._headers(),
                )
                if response.status_code != 201:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def delete_project(self, project_id: str) -> None:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.delete(
                    f"{self.base_url}/api/projects/{project_id}",
                    headers=self._headers(),
                )
                if response.status_code not in (200, 204):
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def list_plans(self, project_id: str = None) -> list:
        self._check_auth()
        try:
            async with self._client() as client:
                params = {}
                if project_id:
                    params["project_id"] = project_id
                response = await client.get(
                    f"{self.base_url}/api/plans",
                    params=params,
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json().get("plans", [])
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def list_public_plans(self) -> list:
        try:
            async with self._client() as client:
                response = await client.get(
                    f"{self.base_url}/api/plans/public",
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json().get("plans", [])
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def get_plan(self, plan_id: str) -> dict:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.get(
                    f"{self.base_url}/api/plans/{plan_id}",
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def create_plan(self, project_id: str, title: str, html_content: str, frontmatter: dict = None, is_public: bool = False) -> dict:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.post(
                    f"{self.base_url}/api/plans",
                    json={
                        "project_id": project_id,
                        "title": title,
                        "html_content": html_content,
                        "frontmatter": frontmatter,
                        "is_public": is_public,
                    },
                    headers=self._headers(),
                )
                if response.status_code != 201:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def update_plan(self, plan_id: str, **kwargs) -> dict:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.put(
                    f"{self.base_url}/api/plans/{plan_id}",
                    json=kwargs,
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def delete_plan(self, plan_id: str) -> None:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.delete(
                    f"{self.base_url}/api/plans/{plan_id}",
                    headers=self._headers(),
                )
                if response.status_code not in (200, 204):
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def publish_plan(self, plan_id: str) -> dict:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.post(
                    f"{self.base_url}/api/plans/{plan_id}/publish",
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def unpublish_plan(self, plan_id: str) -> dict:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.post(
                    f"{self.base_url}/api/plans/{plan_id}/unpublish",
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def archive_plan(self, plan_id: str) -> dict:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.post(
                    f"{self.base_url}/api/plans/{plan_id}/archive",
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def unarchive_plan(self, plan_id: str) -> dict:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.post(
                    f"{self.base_url}/api/plans/{plan_id}/unarchive",
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def archive_project(self, project_id: str) -> dict:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.post(
                    f"{self.base_url}/api/projects/{project_id}/archive",
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)

    async def unarchive_project(self, project_id: str) -> dict:
        self._check_auth()
        try:
            async with self._client() as client:
                response = await client.post(
                    f"{self.base_url}/api/projects/{project_id}/unarchive",
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    raise PlanAPIError(response.status_code, _get_error_detail(response))
                return response.json()
        except httpx.ConnectError:
            raise PlanConnectionError(self.base_url)
