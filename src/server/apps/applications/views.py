import logging
import os
import uuid
import subprocess
from http import HTTPStatus
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseBadRequest, JsonResponse
from django.views.decorators.http import require_GET

from application.officesud.System import dataloader, sqlite as office_sqlite  # NEW
from server.apps.applications.models import OfficeSudTask  # NEW

PLAYWRIGHT_IMAGE = getattr(settings, "OFFICESUD_PLAYWRIGHT_IMAGE", "dj_pw_officesud_worker:latest")
UPLOAD_DIR = getattr(settings, "OFFICESUD_UPLOAD_DIR", Path(settings.BASE_DIR) / "officesud_uploads")
MAX_WORKERS = getattr(settings, "PLAYWRIGHT_MAX_WORKERS", 3)

DOCKER_DJANGO_CONTAINER = getattr(settings, "DOCKER_DJANGO_CONTAINER", "app")

db_host_dir = str(settings.OFFICESUD_DB_DIR)  # src/officesud_db

logger = logging.getLogger(__name__)


@login_required
def start_officesud_batch(request: HttpRequest):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    user = request.user  # NEW

    user_has_active = OfficeSudTask.objects.filter(
        user=user,
        status__in=[OfficeSudTask.STATUS_PENDING, OfficeSudTask.STATUS_RUNNING],
    ).exists()

    if user_has_active:
        return JsonResponse(
            {
                "error": "У вас уже запущена задача Office.sud. "
                         "Дождитесь её завершения перед запуском новой.",
                "code": "user_task_already_running",
            },
            status=HTTPStatus.CONFLICT,
        )

    active_tasks = OfficeSudTask.objects.filter(
        status__in=[OfficeSudTask.STATUS_PENDING, OfficeSudTask.STATUS_RUNNING],
    ).count()

    if active_tasks >= MAX_WORKERS:
        return JsonResponse(
            {
                "error": "Сервер сейчас обрабатывает максимум параллельных задач. "
                         "Попробуйте ещё раз через несколько минут.",
                "code": "global_limit_reached",
            },
            status=HTTPStatus.TOO_MANY_REQUESTS,
        )

    excel_file = request.FILES.get("excel_file")
    if not excel_file:
        return HttpResponseBadRequest("Требуется загрузить EXCEL-файл")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    ext = os.path.splitext(excel_file.name)[1]
    filename = f"{user.id}_{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / filename

    with file_path.open("wb+") as dest:
        for chunk in excel_file.chunks():
            dest.write(chunk)
    logger.info(
        "OfficeSud batch start requested by user_id=%s, filename=%s, size=%s bytes",
        user.id,
        excel_file.name,
        excel_file.size,
    )
    logger.info(
        "Using OFFICESUD_DB_PATH=%s",
        settings.OFFICESUD_DB_PATH,
    )
    try:
        logger.info("Initializing OfficeSud SQLite DB...")
        office_sqlite.check_and_initialize_db()
        logger.info("DB initialized, loading Excel into DB from %s", file_path)

        batch_id = dataloader.load_excel_to_db(str(file_path))
        logger.info("Excel loaded to DB successfully, batch_id=%s", batch_id)

        try:
            file_path.unlink()
            logger.info("Uploaded Excel file %s deleted after import", file_path)
        except OSError as e:
            logger.warning("Не удалось удалить Excel %s: %s", file_path, e)
    except Exception as e:
        logger.exception(
            "Excel parsing/DB load failed for user_id=%s, file=%s",
            user.id,
            file_path,
        )
        return JsonResponse(
            {
                "error": f"Ошибка при разборе Excel-файла: {e}",
                "code": "excel_load_error",
            },
            status=HTTPStatus.BAD_REQUEST,
        )
    task = OfficeSudTask.objects.create(
        user=user,
        excel_file=str(filename),
        batch_id=batch_id,
        status=OfficeSudTask.STATUS_PENDING,
    )
    logger.info(
        "OfficeSudTask created: id=%s, batch_id=%s, user_id=%s",
        task.pk,
        batch_id,
        user.id,
    )
    try:
        logger.info("Starting worker for batch_id=%s", batch_id)
        container_id = subprocess.check_output(
            [
                "docker", "run", "-d", "--rm",
                "--volumes-from", DOCKER_DJANGO_CONTAINER,
                "-e", f"OFFICESUD_DB_PATH={settings.OFFICESUD_DB_PATH}",
                PLAYWRIGHT_IMAGE,
                batch_id,  # <-- передаём batch_id, а не путь к файлу
            ],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
        logger.info(
            "Worker started for batch_id=%s, container_id=%s",
            batch_id,
            container_id,
        )
    except subprocess.CalledProcessError as e:
        logger.error(
            "Failed to start worker for %s: code=%s, output=%r",
            batch_id, e.returncode, e.output,
        )
        task.status = OfficeSudTask.STATUS_ERROR
        task.last_error = e.output
        task.save(update_fields=["status", "last_error", "updated_at"])
        return JsonResponse({"error": "Failed to start worker"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    task.container_id = container_id
    task.status = OfficeSudTask.STATUS_RUNNING
    task.save(update_fields=["status", "container_id", "updated_at"])

    return JsonResponse(
        {
            "status": "started",
            "file": filename,
            "task_id": task.pk,
            "batch_id": batch_id,
        }
    )


@login_required
@require_GET
def get_officesud_progress(request: HttpRequest, task_id: int):
    try:
        task = OfficeSudTask.objects.get(pk=task_id, user=request.user)
    except OfficeSudTask.DoesNotExist:
        return JsonResponse({"error": "Задача не найдена"}, status=HTTPStatus.NOT_FOUND)

    batch_id = task.batch_id
    if not batch_id:
        return JsonResponse(
            {
                "status": task.status,
                "progress": 0,
                "processed": 0,
                "total": 0,
            }
        )

    try:
        processed, total = office_sqlite.get_batch_progress(batch_id)
    except Exception as exc:
        task.status = OfficeSudTask.STATUS_ERROR
        task.last_error = str(exc)
        task.save(update_fields=["status", "last_error", "updated_at"])
        return JsonResponse(
            {
                "status": OfficeSudTask.STATUS_ERROR,
                "error": "Ошибка чтения прогресса из SQLite",
            },
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    if total <= 0:
        percent = 0
    else:
        percent = int((processed / total) * 100)

    if percent >= 100 and task.status != OfficeSudTask.STATUS_SUCCESS:
        task.status = OfficeSudTask.STATUS_SUCCESS
        task.save(update_fields=["status", "updated_at"])

    return JsonResponse(
        {
            "status": task.status,
            "progress": percent,
            "processed": processed,
            "total": total,
        }
    )