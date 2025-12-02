from application.officesud.System import sqlite, dataloader
from application.officesud.System.case_processor import CaseProcessor
from application.officesud.System.modal import logger


class DummyStopEvent:
    @staticmethod
    def is_set() -> bool:
        return False

def run_batch_from_excel(excel_path: str) -> str:
    sqlite.check_and_initialize_db()

    batch_id = dataloader.load_excel_to_db(excel_path)

    stop_event = DummyStopEvent()
    processor = CaseProcessor(batch_id=batch_id, stop_event=stop_event)
    processor.run_process()

    return batch_id

if __name__ == '__main__':
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Run Office.sud.kz batch via Playwright")
    parser.add_argument("excel_path", type=str, help="Путь до Excel-файла с делами")
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise SystemExit(f"Excel-файл не найден: {excel_path}")

    batch_id = run_batch_from_excel(str(excel_path))
    logger.info("Batch processed: %s", batch_id)
