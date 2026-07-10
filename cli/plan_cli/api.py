import httpx
from plan_cli.config import get_api_key, get_api_url


class PlanAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API Error {status_code}: {detail}")


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

    async def register(self, email: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/auth/register",
                json={"email": email},
            )
            if response.status_code != 201:
                raise PlanAPIError(response.status_code, _get_error_detail(response))
            return response.json()

    async def login(self, email: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/auth/login",
                json={"email": email},
            )
            if response.status_code != 200:
                raise PlanAPIError(response.status_code, _get_error_detail(response))
            return response.json()

    async def list_projects(self) -> list:
        self._check_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/projects",
                headers=self._headers(),
            )
            if response.status_code != 200:
                raise PlanAPIError(response.status_code, _get_error_detail(response))
            return response.json().get("projects", [])

    async def get_project(self, project_id: str) -> dict:
        self._check_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/projects/{project_id}",
                headers=self._headers(),
            )
            if response.status_code != 200:
                raise PlanAPIError(response.status_code, _get_error_detail(response))
            return response.json()

    async def create_project(self, name: str, description: str = None) -> dict:
        self._check_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
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

    async def delete_project(self, project_id: str) -> None:
        self._check_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/api/projects/{project_id}",
                headers=self._headers(),
            )
            if response.status_code not in (200, 204):
                raise PlanAPIError(response.status_code, _get_error_detail(response))

    async def list_plans(self, project_id: str = None, public: bool = False) -> list:
        self._check_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {}
            if project_id:
                params["project_id"] = project_id
            if public:
                params["public"] = True
            response = await client.get(
                f"{self.base_url}/api/plans",
                params=params,
                headers=self._headers(),
            )
            if response.status_code != 200:
                raise PlanAPIError(response.status_code, _get_error_detail(response))
            return response.json().get("plans", [])

    async def list_public_plans(self) -> list:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/plans/public",
            )
            if response.status_code != 200:
                raise PlanAPIError(response.status_code, _get_error_detail(response))
            return response.json().get("plans", [])

    async def get_plan(self, plan_id: str) -> dict:
        self._check_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/plans/{plan_id}",
                headers=self._headers(),
            )
            if response.status_code != 200:
                raise PlanAPIError(response.status_code, _get_error_detail(response))
            return response.json()

    async def create_plan(self, project_id: str, title: str, html_content: str, frontmatter: dict = None, is_public: bool = False) -> dict:
        self._check_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
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

    async def update_plan(self, plan_id: str, **kwargs) -> dict:
        self._check_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{self.base_url}/api/plans/{plan_id}",
                json=kwargs,
                headers=self._headers(),
            )
            if response.status_code != 200:
                raise PlanAPIError(response.status_code, _get_error_detail(response))
            return response.json()

    async def delete_plan(self, plan_id: str) -> None:
        self._check_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/api/plans/{plan_id}",
                headers=self._headers(),
            )
            if response.status_code not in (200, 204):
                raise PlanAPIError(response.status_code, _get_error_detail(response))

    async def publish_plan(self, plan_id: str) -> dict:
        self._check_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/plans/{plan_id}/publish",
                headers=self._headers(),
            )
            if response.status_code != 200:
                raise PlanAPIError(response.status_code, _get_error_detail(response))
            return response.json()

    async def unpublish_plan(self, plan_id: str) -> dict:
        self._check_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/plans/{plan_id}/unpublish",
                headers=self._headers(),
            )
            if response.status_code != 200:
                raise PlanAPIError(response.status_code, _get_error_detail(response))
            return response.json()
