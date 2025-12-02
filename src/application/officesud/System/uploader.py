# System/uploader.py
import os
import time
from playwright.sync_api import Page, expect
from .logger import get_logger
import random

log = get_logger("Uploader")

class FileUploader:
    def __init__(self, page: Page):
        self.page = page

    def upload_file(self, button_name, file_paths_string):
        paths = [p.strip() for p in file_paths_string.split('*') if p.strip()]
        if not paths:
            return
        absolute_paths = []
        for file_name in paths:
            file_path = os.path.abspath(file_name)
            if not os.path.exists(file_path):
                log.error(f"Файл не найден и пропущен: {file_path}")
            else:
                absolute_paths.append(file_path)
        if not absolute_paths:
            return
        with self.page.expect_file_chooser() as fc_info:
            self.page.get_by_role("button", name=button_name).first.click()
        file_chooser = fc_info.value
        file_chooser.set_files(absolute_paths)
        time.sleep(random.uniform(1, 2)) 


    def handle_payment_files(self, PaymentDocPath):
        checkbox = self.page.locator("input[name$='isonline-payment']")
        if not checkbox.is_checked():
            checkbox.check()
            time.sleep(random.uniform(1, 2))
        self.upload_file("Файлды қоса тіркеу", PaymentDocPath)
