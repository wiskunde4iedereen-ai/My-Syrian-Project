import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.templating import _TemplateResponse
from starlette.requests import Request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_env = Environment(
    loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")),
    autoescape=select_autoescape(),
    enable_async=False,
)


def render(name: str, request: Request, **context):
    template = _env.get_template(name)
    ctx = {"request": request, **context}
    if "user" not in ctx:
        user = getattr(request.state, "user", None)
        if user:
            ctx["user"] = user
    if "show_nav" not in ctx and "user" in ctx and ctx["user"]:
        ctx["show_nav"] = True
    if "user_role" not in ctx:
        role = getattr(request.state, "role", None)
        if role:
            ctx["user_role"] = role
    if "employee" not in ctx:
        emp = getattr(request.state, "employee", None)
        if emp:
            ctx["employee"] = emp
    if "is_planning_director" not in ctx:
        emp = getattr(request.state, "employee", None)
        role = getattr(request.state, "role", None)
        ctx["is_planning_director"] = bool(emp and role and emp.department_id == 4 and role.name == "مدير مديرية")
    return _TemplateResponse(template, ctx, media_type="text/html")
