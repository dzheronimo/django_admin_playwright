# System/modal.py

from playwright.sync_api import Page, expect, Locator
import logging
from typing import Optional
import re
import time
import random

logger = logging.getLogger(__name__)

class ParticipantModal:

    ADD_PARTICIPANT_BUTTON: str = 'button:has-text("Процесс қатысушысын қосу")'
    MODAL_SELECT_SIDE: str = '#selectSideModalDialog'
    PERSON_TYPE_SELECT: str = f'{MODAL_SELECT_SIDE} select[id$=":pp-type"]'
    PARTICIPANT_SIDE_SELECT: str = f'{MODAL_SELECT_SIDE} select[id$=":pp-side"]'
    NEXT_BUTTON_SELECT_SIDE: str = f'{MODAL_SELECT_SIDE} input[value="Ары қарай"]'
    

    MODAL_JURIDICAL: str = '#jurModalDialog'
    BIN_TEXTBOX_JUR: str = 'input[id$=":org-bin"]'
    FACT_ADDRESS_TEXTBOX: str = 'input[name$=":org-factAddress"]'
    BANK_DETAILS_TEXTBOX: str = 'input[name$=":org-bankDetails"]'
    SAVE_BUTTON_JUR: str = f'{MODAL_JURIDICAL} input[value="Сақтау"]'
    GBD_SEARCH_JUR: str = f'{MODAL_JURIDICAL} .gbdSearch'
    

    MODAL_PHYSICAL: str = '#fizModalDialog'
    IIN_TEXTBOX_PHYS: str = 'input[id$=":person-iin"]'
    PHONE_TEXTBOX: str = 'input[id$=":person-phone"]'
    EMAIL_TEXTBOX: str = 'input[id$=":person-email"]'
    SAVE_BUTTON_PHYS: str = f'{MODAL_PHYSICAL} input[value="Сақтау"]'
    GBD_SEARCH_PHYS: str = f'{MODAL_PHYSICAL} .gbdSearch'
    

    LOADER: str = '.loader'
    RICHFACES_STATUS_STOP: str = '.rf-st-stop[style=""]'

    def __init__(self, page: Page):
        self.page: Page = page


    def _wait_for_loader(self, timeout: int = 15000) -> None:
        try:
            loader_locator = self.page.locator(self.LOADER)
            expect(loader_locator).to_have_class(re.compile(r'd-none'), timeout=timeout)
        except Exception:
            logger.warning("Loader did not disappear, continuing execution.")

    def _wait_for_richfaces_stop(self, timeout: int = 15000) -> None:
        try:
            stop_locator = self.page.locator(self.RICHFACES_STATUS_STOP)
            stop_locator.wait_for(state="attached", timeout=timeout)
            logger.info("RichFaces AJAX stop indicator found.")
        except Exception:
            logger.warning("RichFaces AJAX stop indicator not found/not attached in time.")

    def _handle_modal_click(self, locator: Locator) -> None:

        self._wait_for_loader()
        button = locator

        if button.is_visible():
            button.click()
            self._wait_for_richfaces_stop()
            return

        self.page.locator('body').focus()
        
        if button.is_visible():
            button.click()
            self._wait_for_richfaces_stop()
            return
        
        logger.warning("Add participant button still not visible. Clicking with force=True.")
        button.click(force=True)
        self._wait_for_richfaces_stop()

    def _check_modal_visibility(self, modal_selector: str, modal_name: str) -> None:
 
        if not self.page.locator(modal_selector).is_visible():
            error_msg = f"Modal window **{modal_name} ({modal_selector})** disappeared unexpectedly. Must retry from step 1."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        logger.debug(f"Modal **{modal_name}** is visible. Continuing.")
        
    def _handle_modal_fill_and_next(self, modal_locator: str, next_button_locator: str) -> bool:

        self._check_modal_visibility(modal_locator, "Select Side Modal")

        self.page.locator(next_button_locator).click()
        self._wait_for_richfaces_stop()
        
        return True

    def add_participant(self, side_value: str, is_juridical: bool) -> bool:

        
        add_button = self.page.locator(self.ADD_PARTICIPANT_BUTTON)
        self._handle_modal_click(add_button)

        modal_locator = self.MODAL_SELECT_SIDE
        try:
            self.page.locator(modal_locator).wait_for(state="visible", timeout=10000)
        except Exception:
            logger.error(f"First modal window {modal_locator} is not visible after clicking button.")
            return False

        person_type_option = "true" if is_juridical else "false"
        self.page.locator(self.PERSON_TYPE_SELECT).select_option(person_type_option)
        self._wait_for_richfaces_stop()

        self.page.locator(self.PARTICIPANT_SIDE_SELECT).select_option(str(side_value))
        self._wait_for_richfaces_stop()

        return self._handle_modal_fill_and_next(modal_locator, self.NEXT_BUTTON_SELECT_SIDE)


    def fill_juridical_data(self, bin_num: str, address: str, bank_details: str) -> None:

        modal_selector = self.MODAL_JURIDICAL
        
        try:
            self.page.locator(modal_selector).wait_for(state="visible", timeout=10000)
        except Exception:
            raise RuntimeError(f"Juridical modal window {modal_selector} did not appear/is not visible.")
        
        self._wait_for_loader()
        self._check_modal_visibility(modal_selector, "Juridical Modal (Start)")

        bin_input = self.page.locator(self.BIN_TEXTBOX_JUR)
        bin_input.type(bin_num, delay=50)
        time.sleep(random.uniform(1, 2))
        self._check_modal_visibility(modal_selector, "Juridical Modal (Post-BIN Input)")
        
        self.page.locator(self.GBD_SEARCH_JUR).click()
        self._wait_for_loader()
        time.sleep(random.uniform(1, 2))
        self._check_modal_visibility(modal_selector, "Juridical Modal (Post-GBD Search)")

        self.page.locator(self.FACT_ADDRESS_TEXTBOX).fill(address)
        time.sleep(random.uniform(1, 2))
        self._check_modal_visibility(modal_selector, "Juridical Modal (Post-Address Input)")
        
        self.page.locator(self.BANK_DETAILS_TEXTBOX).fill(bank_details)
        time.sleep(random.uniform(1, 2))
        self._check_modal_visibility(modal_selector, "Juridical Modal (Post-Bank Details Input)")

        self.page.locator(self.SAVE_BUTTON_JUR).click()
        self._wait_for_loader()


    def fill_physical_data(self, iin: str, phone: Optional[str] = None, email: Optional[str] = None) -> None:

        modal_selector = self.MODAL_PHYSICAL
        
        try:
            self.page.locator(modal_selector).wait_for(state="visible", timeout=10000)
        except Exception:
            raise RuntimeError(f"Physical modal window {modal_selector} did not appear/is not visible.")
            
        self._wait_for_loader()
        self._check_modal_visibility(modal_selector, "Physical Modal (Start)")

        iin_input = self.page.locator(self.IIN_TEXTBOX_PHYS)
        iin_input.type(iin , delay=50)
        
        self._check_modal_visibility(modal_selector, "Physical Modal (Post-IIN Input)")
            
        self.page.locator(self.GBD_SEARCH_PHYS).click()
        
        self._wait_for_loader() 
        self._wait_for_richfaces_stop() 
        time.sleep(random.uniform(1, 2))
        
        self._check_modal_visibility(modal_selector, "Physical Modal (Post-GBD Search)")
        
        if phone:
            phone_locator = self.page.locator(self.PHONE_TEXTBOX)
            
            try:
                phone_locator.wait_for(state="visible", timeout=5000) 
            except Exception:
                logger.error(f"Phone field {self.PHONE_TEXTBOX} is not visible/ready.")
                raise RuntimeError("Phone field is not ready for input.")
                

            phone_locator.clear()
            phone_locator.type(phone, delay=50) 
            time.sleep(random.uniform(1, 2))
            
            self._check_modal_visibility(modal_selector, "Physical Modal (Post-Phone Input)")
        
        if email:
            self.page.locator(self.EMAIL_TEXTBOX).type(email, delay=60)
            time.sleep(random.uniform(1, 2))

            self._check_modal_visibility(modal_selector, "Physical Modal (Post-Email Input)")

        self._check_modal_visibility(modal_selector, "Physical Modal (Pre-Save)")

        self.page.locator(self.SAVE_BUTTON_PHYS).click()
        
        self._wait_for_loader()