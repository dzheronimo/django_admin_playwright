# System/case_processor.py
import time
import os
from playwright.sync_api import sync_playwright
from .logger import get_logger
from . import sqlite
import random
import threading

log = get_logger("CaseProcessor")

class CaseProcessor:
    def __init__(self, batch_id, stop_event: threading.Event):
        self.batch_id = batch_id
        self.stop_event = stop_event
        self.internal_ids_to_process = sqlite.get_unique_internal_ids(batch_id)

    def _process_single_case(self, filler, case_data):
     
        internal_id = case_data["InternalID"]
        
        filler.open_lawsuit_filing_form(
            case_data["RegionID"],
            case_data["CourtID"]
        )

        self._add_participants(filler, case_data)

        filler.fill_payment_and_lawsuit_data(
            PaymentDocPath=case_data["PaymentDocPath"],
            MainDocPath=case_data["MainDocPath"],
            OtherDocPath=case_data["OtherDocPath"],
            ClaimSummary=case_data["ClaimSummary"],
            ClaimBasis=case_data["ClaimBasis"],
            ClaimAmount=case_data["ClaimAmount"],
            StateDuty=case_data["StateDuty"]
        )
        
        filler.save_talonid(internal_id)
        log.info(f"Дело {internal_id} (Ответчик ID: {case_data.get('DefendantID', 'N/A')}) успешно подготовлено.")

        filler.return_to_cabinet_home()

    def _add_participants(self, filler, data):
        
        def get_split_list(key, num_participants, enforce_list=False):

            value = data.get(key)
            if value is None or not isinstance(value, str) or value.strip() == "":
                return [None] * num_participants
            
            split_values = [v.strip() for v in value.split('*')]
            
            if enforce_list and len(split_values) == 1 and num_participants > 0:
                return [split_values[0]] * num_participants
            
            if num_participants > 0:
                return split_values + [None] * (num_participants - len(split_values))
            return split_values

        plaintiff_ids_raw = data.get("PlaintiffID")
        plaintiff_ids = [v.strip() for v in plaintiff_ids_raw.split('*')] if plaintiff_ids_raw else []
        num_plaintiffs = len(plaintiff_ids) if plaintiff_ids and plaintiff_ids[0] else 0

        plaintiff_sides = get_split_list("PlaintiffSide", num_plaintiffs, enforce_list=True)
        plaintiff_types = get_split_list("PlaintiffType", num_plaintiffs, enforce_list=True)
        
        plaintiff_addresses = get_split_list("PlaintiffAddress", num_plaintiffs, enforce_list=False)
        plaintiff_banks = get_split_list("PlaintiffBank", num_plaintiffs, enforce_list=False)
        plaintiff_phones = get_split_list("PlaintiffPhone", num_plaintiffs, enforce_list=False)
        plaintiff_emails = get_split_list("PlaintiffEmail", num_plaintiffs, enforce_list=False)
        
        for i in range(num_plaintiffs):
            filler.add_participant(
                side_value=plaintiff_sides[i], 
                participant_type=plaintiff_types[i],
                id_value=plaintiff_ids[i], 
                address=plaintiff_addresses[i] if plaintiff_addresses[i] else "",
                bank_details=plaintiff_banks[i] if plaintiff_banks[i] else "", 
                phone=plaintiff_phones[i] if plaintiff_phones[i] else "",
                email=plaintiff_emails[i] if plaintiff_emails[i] else ""
            )

        defendant_ids_raw = data.get("DefendantID")
        defendant_ids = [v.strip() for v in defendant_ids_raw.split('*')] if defendant_ids_raw else []
        num_defendants = len(defendant_ids) if defendant_ids and defendant_ids[0] else 0

        defendant_sides = get_split_list("DefendantSide", num_defendants, enforce_list=True)
        defendant_types = get_split_list("DefendantType", num_defendants, enforce_list=True)
        
        defendant_phones = get_split_list("DefendantPhone", num_defendants, enforce_list=False)
        defendant_emails = get_split_list("DefendantEmail", num_defendants, enforce_list=False)
        
        for i in range(num_defendants):
            filler.add_participant(
                side_value=defendant_sides[i], 
                participant_type=defendant_types[i], 
                id_value=defendant_ids[i], 
                address="", 
                bank_details="",
                phone=defendant_phones[i] if defendant_phones[i] else "",
                email=defendant_emails[i] if defendant_emails[i] else ""
            )

        rep_ids_raw = data.get("RepID")
        rep_ids = [v.strip() for v in rep_ids_raw.split('*')] if rep_ids_raw else []
        num_reps = len(rep_ids) if rep_ids and rep_ids[0] else 0

        if num_reps > 0:
            rep_sides = get_split_list("RepSide", num_reps, enforce_list=True)
            rep_types = get_split_list("RepType", num_reps, enforce_list=True)
            rep_addresses = get_split_list("RepAddress", num_reps, enforce_list=False)
            rep_banks = get_split_list("RepBank", num_reps, enforce_list=False)
            rep_phones = get_split_list("RepPhone", num_reps, enforce_list=False)
            rep_emails = get_split_list("RepEmail", num_reps, enforce_list=False)

            for i in range(num_reps):
                filler.add_participant(
                    side_value=rep_sides[i], 
                    participant_type=rep_types[i], 
                    id_value=rep_ids[i], 
                    address=rep_addresses[i] if rep_addresses[i] else "",
                    bank_details=rep_banks[i] if rep_banks[i] else "", 
                    phone=rep_phones[i] if rep_phones[i] else "",
                    email=rep_emails[i] if rep_emails[i] else ""
                )

    def run_process(self):
        from .config import HEADLESS

        from .filler import Filler

        if not self.internal_ids_to_process:
            return

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=HEADLESS, slow_mo=1000, channel="chrome")
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            filler = Filler(page)
            
            filler.starting_process()

            for internal_id in self.internal_ids_to_process:

                if self.stop_event.is_set():
                    break

                case_data = sqlite.get_case_data_by_internal_id(internal_id)
                if not case_data:
                    continue
                    
                if case_data.get("TalonID"):
                    log.info(f"Дело {internal_id} пропущено: TalonID (значение: {case_data['TalonID']}) уже имеется.")
                    continue
                
                log.info(f"Начало дела №: {internal_id} | Ответчик: {case_data.get('DefendantID', 'N/A')}")
                self._process_single_case(filler, case_data)

            context.close()

def start_processing(batch_id, stop_event: threading.Event):
    processor = CaseProcessor(batch_id, stop_event)
    processor.run_process()