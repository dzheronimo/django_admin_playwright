import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest, HttpResponseBadRequest
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import BrowserAgentKey, BrowserCommand


def _get_user_by_token(token: str):
    try:
        agent_key = BrowserAgentKey.objects.select_related("user").get(key=token)
    except BrowserAgentKey.DoesNotExist:
        return None, None
    return agent_key, agent_key.user


@csrf_exempt
def agent_ping(request: HttpRequest):
    """
    POST /api/agent/ping/
    body: { "token": "...", "status": "idle" | "busy", "url": "..." }
    Пока просто валидируем токен.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    token = data.get("token")
    if not token:
        return HttpResponseBadRequest("Token required")

    agent_key, user = _get_user_by_token(token)
    if not user:
        return JsonResponse({"error": "Invalid token"}, status=401)

    # Здесь можно хранить last_seen, статус и т.п. в отдельной модели,
    # но для MVP просто вернём ok.
    return JsonResponse({"status": "ok", "server_time": timezone.now().isoformat()})


@csrf_exempt
def agent_next_command(request: HttpRequest):
    """
    GET /api/agent/next-command/?token=...
    Возвращает одну PENDING-команду для пользователя или пусто.
    """
    if request.method != "GET":
        return HttpResponseBadRequest("GET only")

    token = request.GET.get("token")
    if not token:
        return HttpResponseBadRequest("Token required")

    agent_key, user = _get_user_by_token(token)
    if not user:
        return JsonResponse({"error": "Invalid token"}, status=401)

    cmd = (
        BrowserCommand.objects
        .filter(user=user, status=BrowserCommand.STATUS_PENDING)
        .order_by("created_at")
        .first()
    )
    if not cmd:
        return JsonResponse({"command": None})

    # помечаем как отправленную
    cmd.status = BrowserCommand.STATUS_SENT
    cmd.save(update_fields=["status", "updated_at"])

    return JsonResponse(
        {
            "command": {
                "id": cmd.id,
                "type": cmd.type,
                "payload": cmd.payload,
            }
        }
    )


@csrf_exempt
def agent_report_result(request: HttpRequest):
    """
    POST /api/agent/command-result/
    body: { "token": "...", "command_id": 123, "status": "done"|"error", "result_text": "..." }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    token = data.get("token")
    cmd_id = data.get("command_id")
    new_status = data.get("status")
    result_text = data.get("result_text", "")

    if not (token and cmd_id and new_status):
        return HttpResponseBadRequest("token, command_id and status are required")

    if new_status not in (BrowserCommand.STATUS_DONE, BrowserCommand.STATUS_ERROR):
        return HttpResponseBadRequest("Invalid status")

    agent_key, user = _get_user_by_token(token)
    if not user:
        return JsonResponse({"error": "Invalid token"}, status=401)

    try:
        cmd = BrowserCommand.objects.get(id=cmd_id, user=user)
    except BrowserCommand.DoesNotExist:
        return JsonResponse({"error": "Command not found"}, status=404)

    cmd.status = new_status
    cmd.result_text = result_text
    cmd.save(update_fields=["status", "result_text", "updated_at"])

    return JsonResponse({"status": "ok"})


def agent_get_token(request: HttpRequest):
    """
    GET /api/agent/token/

    Возвращает JSON с токеном для текущего авторизованного пользователя.
    Использует Django-сессию (куку). Если пользователь не залогинен —
    возвращает 401, чтобы расширение понимало, что надо сначала авторизоваться.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "auth_required"}, status=401)

    agent_key, created = BrowserAgentKey.objects.get_or_create(
        user=request.user,
        defaults={"key": BrowserAgentKey.generate_key()},
    )

    return JsonResponse(
        {
            "token": agent_key.key,
            "user_id": request.user.id,
            "username": request.user.get_username(),
            "created_at": agent_key.created_at.isoformat(),
            "server_time": timezone.now().isoformat(),
        }
    )


@login_required
def show_agent_token(request: HttpRequest):
    """
    HTML-страница с токеном (если захочешь посмотреть/скопировать вручную).
    Сейчас она живёт по адресу /api/agent/token-page/
    """
    agent_key, created = BrowserAgentKey.objects.get_or_create(
        user=request.user,
        defaults={"key": BrowserAgentKey.generate_key()},
    )
    return render(request, "browser_agent/token.html", {"agent_key": agent_key})
