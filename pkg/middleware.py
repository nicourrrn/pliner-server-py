from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import json


class PrintHttpRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        body = await request.body()
        try:
            json_body = json.loads(body)
            print("Received JSON:", json.dumps(json_body, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(f"No JSON body or invalid JSON.\n{body.decode('utf-8')}")

        response = await call_next(request)
        return response
