# System/filler.py
import time
import random
from playwright.sync_api import Page, expect, TimeoutError
from .logger import get_logger
from .uploader import FileUploader
from .modal import ParticipantModal
import xml.etree.ElementTree as ET
from . import sqlite

log = get_logger("Filler")


class Filler:
    def __init__(self, page: Page):
        self.page = page
        self.uploader = FileUploader(page)
        self.modal = ParticipantModal(page)
        log.debug("Filler initialized with new Playwright page")

    def wait_loader(self, timeout: int = 100000):
        loader = self.page.locator(".loader")
        if loader.count() > 0:
            log.debug("Waiting for loader to disappear (timeout=%s ms)", timeout)
            loader.wait_for(state="hidden", timeout=timeout)
        else:
            log.debug("Loader element not found, skipping wait")
        sleep_time = random.uniform(1, 2)
        log.debug("Extra sleep after loader: %.2f sec", sleep_time)
        time.sleep(sleep_time)

    def starting_process(self):
        log.info("Opening cabinet home page")
        self.page.goto("https://office.sud.kz/", timeout=0)

    def open_lawsuit_filing_form(self, RegionID, CourtID):
        log.info("Opening lawsuit filing form (RegionID=%s, CourtID=%s)", RegionID, CourtID)
        self.page.wait_for_load_state("domcontentloaded", timeout=0)

        self.page.get_by_role("link", name="Құжаттарды жіберу").click()
        self.wait_loader()

        self.page.get_by_label("Сот ісін жүргізу түрі").select_option("CIVIL")
        self.wait_loader()

        self.page.get_by_label("Саты").select_option("FIRSTINSTANCE")
        self.page.get_by_label("Құжат түрі").select_option("3")
        self.wait_loader()

        self.page.get_by_role("button", name="Жіберу").click()
        self.wait_loader()

        self.page.get_by_label("Іс бойынша іс жүргізу түрі").select_option("2")
        self.wait_loader()
        self.page.get_by_label("Іс санаты").select_option("27")
        self.wait_loader()
        self.page.get_by_label("Арыз сипаты").select_option("1")
        self.wait_loader()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                log.debug("Attempt %s to select Region/Court", attempt + 1)
                self.page.get_by_label(
                    "Облыс (астана, республикалық маңызы бар қала)"
                ).select_option(str(RegionID))
                time.sleep(random.uniform(1, 2))
                court_selector = self.page.get_by_label("Сот органы")
                if court_selector.is_visible(timeout=10000):
                    court_selector.select_option(str(CourtID))
                    time.sleep(random.uniform(2, 3))
                    log.info("Region/Court successfully selected")
                    return
                else:
                    log.warning("Court selector not visible on attempt %s", attempt + 1)
            except Exception:
                log.exception("Error while selecting Region/Court on attempt %s", attempt + 1)

            if attempt < max_retries - 1:
                log.debug("Retrying region/court selection")
                self.page.get_by_label("Іс бойынша іс жүргізу түрі").select_option("2")
                self.page.get_by_label("Іс санаты").select_option("27")
                self.page.get_by_label("Арыз сипаты").select_option("1")
                time.sleep(random.uniform(1, 2))
            else:
                log.error("Failed to select region and court after %s attempts", max_retries)
                raise Exception("Не удалось выбрать регион и суд после нескольких попыток.")

    def add_participant(
        self,
        side_value,
        participant_type,
        id_value,
        address="",
        bank_details="",
        phone="",
        email="",
    ):
        is_jur = str(participant_type).strip() in ["1", "True", "true", "TRUE"]
        log.info(
            "Adding participant: side=%s, is_juridical=%s, id_value=%s",
            side_value,
            is_jur,
            id_value,
        )
        MAX_ATTEMPTS = 3
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                log.debug("add_participant attempt %s", attempt)
                if not self.modal.add_participant(side_value=side_value, is_juridical=is_jur):
                    raise RuntimeError(
                        "First modal step failed to proceed (did not open/disappeared)."
                    )
                if is_jur:
                    self.modal.fill_juridical_data(
                        bin_num=id_value,
                        address=address,
                        bank_details=bank_details or "",
                    )
                else:
                    self.modal.fill_physical_data(
                        iin=id_value,
                        phone=phone or "",
                        email=email or "",
                    )
                time.sleep(random.uniform(1, 3))
                log.info("Participant added successfully")
                return
            except RuntimeError:
                log.warning("Participant modal runtime error on attempt %s", attempt)
                if attempt == MAX_ATTEMPTS:
                    log.error("Giving up after %s attempts", MAX_ATTEMPTS)
                    raise
                time.sleep(random.uniform(1, 3))
                continue
            except Exception:
                log.exception("Unexpected error during add_participant on attempt %s", attempt)
                raise
        time.sleep(random.uniform(1, 2))

    def fill_payment_and_lawsuit_data(
        self,
        PaymentDocPath,
        MainDocPath,
        OtherDocPath,
        ClaimSummary,
        ClaimBasis,
        ClaimAmount,
        StateDuty,
    ):
        log.info(
            "Filling payment and lawsuit data: ClaimAmount=%s, StateDuty=%s, "
            "PaymentDocPath=%s, MainDocPath=%s, OtherDocPath=%s",
            ClaimAmount,
            StateDuty,
            PaymentDocPath,
            MainDocPath,
            OtherDocPath,
        )
        self.page.locator(".button-orange").get_by_text("Ары қарай").click()
        self.wait_loader()

        self.page.get_by_role("combobox").first.select_option("2")
        self.wait_loader()

        self.page.locator("input[name$=':edit-totalSum']").fill(str(ClaimAmount))
        self.wait_loader()
        self.page.locator("input[name$=':edit-duty']").fill(str(StateDuty))

        log.debug("Uploading payment documents")
        self.uploader.handle_payment_files(PaymentDocPath)
        self.wait_loader()

        self.page.locator(".button-orange").get_by_text("Ары қарай").click()
        self.wait_loader()

        text_areas = self.page.locator("textarea")
        ta_count = text_areas.count()
        log.debug("Found %s textareas on lawsuit page", ta_count)

        if ta_count >= 1:
            text_areas.nth(0).fill(ClaimSummary)
            time.sleep(random.uniform(1, 2))
        if ta_count >= 2:
            text_areas.nth(1).fill(ClaimBasis)
            time.sleep(random.uniform(1, 2))

        log.debug("Uploading main and additional documents")
        self.uploader.upload_file("Талап арызды жүктеу", MainDocPath)
        time.sleep(random.uniform(1, 2))
        self.uploader.upload_file("Файлды қоса тіркеу", OtherDocPath)

        try:
            self.page.locator(".loader").wait_for(state="hidden", timeout=60000)
        except TimeoutError:
            log.warning("Timeout while waiting for loader after file upload")

        time.sleep(random.uniform(1, 2))
        self.wait_loader()

        log.debug("Clicking 'Ары қарай' to proceed to next step (before talon)")
        self.page.locator(".button-orange").get_by_text("Ары қарай").click()
        self.page.wait_for_load_state("load")
        log.info("Payment and lawsuit data filled; moved to next page")

    def save_talonid(self, internal_id: str):
        log.info("Attempting to save TalonID for internal_id=%s", internal_id)
        try:
            locator = self.page.locator("#xmlToSign0")
            count = locator.count()
            log.debug("#xmlToSign0 elements found: %s", count)
            if count == 0:
                log.warning("#xmlToSign0 element not found on page; cannot read TalonID")
                return

            xml_value = locator.get_attribute("value")
            if xml_value is None:
                log.warning("xmlToSign0.value is None for internal_id=%s", internal_id)
                return

            if not xml_value.strip():
                log.warning("xmlToSign0.value is empty for internal_id=%s", internal_id)
                return

            preview = xml_value[:300].replace("\n", " ")
            log.debug("xmlToSign0.value preview (first 300 chars): %s", preview)

            xml_string = xml_value.replace("&lt;", "<").replace("&gt;", ">")
            try:
                root = ET.fromstring(xml_string)
            except ET.ParseError:
                log.exception("Failed to parse XML from xmlToSign0 for internal_id=%s", internal_id)
                return

            f1_element = root.find("f1")
            if f1_element is None:
                log.warning("<f1> element not found in XML for internal_id=%s", internal_id)
                return

            talon_id = (f1_element.text or "").strip()
            if not talon_id:
                log.warning(
                    "<f1> element has empty text; cannot derive TalonID (internal_id=%s)",
                    internal_id,
                )
                return

            log.info("Parsed TalonID='%s' for internal_id=%s; updating DB", talon_id, internal_id)
            sqlite.update_case_status(internal_id=internal_id, talon_id=talon_id)
            log.info("TalONID successfully saved in DB for internal_id=%s", internal_id)
        except Exception:
            log.exception("Unexpected error in save_talonid for internal_id=%s", internal_id)

    def return_to_cabinet_home(self):
        wait_sec = random.uniform(10, 15)
        log.debug("Waiting %.2f sec before returning to cabinet home", wait_sec)
        time.sleep(wait_sec)

        log.info("Returning to cabinet home page")
        self.page.goto("https://office.sud.kz/form/proceedings/services.xhtml")
        self.page.get_by_role("link", name="Құжаттарды жіберу").wait_for(
            state="visible", timeout=20000
        )

        after_wait_sec = random.uniform(5, 7)
        log.debug("Extra wait after cabinet home load: %.2f sec", after_wait_sec)
        time.sleep(after_wait_sec)
