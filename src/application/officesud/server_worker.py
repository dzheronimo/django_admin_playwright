# application/officesud/server_worker.py
from application.officesud.System import sqlite  # noqa
from application.officesud.System.case_processor import CaseProcessor
from application.officesud.System.modal import logger


class DummyStopEvent:
    @staticmethod
    def is_set() -> bool:
        return False


def run_batch(batch_id: str) -> str:
    sqlite.check_and_initialize_db()
    processor = CaseProcessor(batch_id=batch_id, stop_event=DummyStopEvent())
    processor.run_process()
    return batch_id


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Office.sud batch by batch_id (server mode)")
    parser.add_argument("batch_id", type=str, help="BatchID, созданный через dataloader.load_excel_to_db(...)")
    args = parser.parse_args()

    logger.info("Starting batch: %s", args.batch_id)
    run_batch(args.batch_id)
    logger.info("Finished batch: %s", args.batch_id)
