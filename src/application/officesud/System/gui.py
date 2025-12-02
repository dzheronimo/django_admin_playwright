# System/gui.py
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
import time
import threading
import logging
import os 
import sqlite, dataloader, config
from .logger import get_logger
import case_processor

log = get_logger("GUI")

console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(console_handler)

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.excel_path = config.SESSION_VARS.get("EXCEL_FILE_PATH")
        
        self.master = master
        self.master.title("Diana")
        self.processing_thread = None
        self.progress_thread = None 
        self.stop_event = threading.Event()
        self.current_batch_id = None
        self.total_cases = 0
        self.pack(padx=10, pady=10)
        self.create_widgets()
        

    def create_widgets(self):

        self.file_frame = tk.LabelFrame(self, text="Выбор Excel-файла", padx=5, pady=5)
        self.file_frame.pack(fill="x", padx=5, pady=5)
        
        initial_file_text = os.path.basename(self.excel_path) if self.excel_path else "Файл не выбран"
        self.file_path_label = tk.Label(self.file_frame, text=initial_file_text, anchor="w")
        self.file_path_label.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        self.select_button = tk.Button(self.file_frame, text="Обзор...", command=self.select_file)
        self.select_button.pack(side="right", padx=5, pady=5)

        initial_state = tk.NORMAL if self.excel_path else tk.DISABLED

        self.process_button = tk.Button(self, text="Начать подачу", command=self.start_processing_thread, state=initial_state, bg="#6A5ACD", fg="white", font=('Arial', 10, 'bold'))
        self.process_button.pack(fill="x", pady=10)

        self.stop_button = tk.Button(self, text="Остановить", command=self.stop_processing, 
                                     state=tk.DISABLED, bg="#FF4500", fg="white", font=('Arial', 10, 'bold'))
        self.stop_button.pack(fill="x", pady=5)
        
        export_initial_state = tk.DISABLED
        self.export_button = tk.Button(self, text="Скачать", 
                                       command=self.export_to_excel_thread, 
                                       state=export_initial_state, bg="#2E8B57", fg="white", font=('Arial', 10, 'bold'))
        self.export_button.pack(fill="x", pady=5)

        self.progress_frame = tk.LabelFrame(self, text="Прогресс пакета", padx=5, pady=5)
        self.progress_frame.pack(fill="x", padx=5, pady=5)

        self.progress_bar = ttk.Progressbar(self.progress_frame, orient='horizontal', length=300, mode='determinate')
        self.progress_bar.pack(fill='x', expand=True, padx=5, pady=5)
        
        self.progress_label = tk.Label(self.progress_frame, text="Ожидание запуска...")
        self.progress_label.pack(fill='x', padx=5, pady=2)
        
        self.log_area = scrolledtext.ScrolledText(self, state='disabled', height=1, width=1, bg="#F0F0F0")
        
    def select_file(self):
        
        initial_dir = os.path.dirname(self.excel_path) if self.excel_path and os.path.exists(self.excel_path) else os.getcwd()
        
        selected_file = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="Выберите Excel-файл",
            filetypes=(("Excel files", "*.xlsx"), ("All files", "*.*"))
        )
        
        if selected_file:
            self.excel_path = selected_file
            self.file_path_label.config(text=f"Выбран файл: {os.path.basename(self.excel_path)}")
            config.save_config_key("EXCEL_FILE_PATH", self.excel_path)
            self.check_can_process()
        else:
            log.warning("Выбор Excel-файла отменен.")

    def stop_processing(self):
        if self.processing_thread and self.processing_thread.is_alive():
            self.stop_event.set()
            log.info("Нажата остановлено. Ожидание завершения текущего дела.")
            self.stop_button.config(state=tk.DISABLED, text="Ожидание завершения...")
            if self.progress_thread and self.progress_thread.is_alive():
                 self.progress_thread_running = False

    def export_to_excel_thread(self):
        if not self.current_batch_id:
            messagebox.showerror("Ошибка", "Сначала необходимо запустить подачу, чтобы определить текущий BatchID.")
            return

        self.export_button.config(state=tk.DISABLED, text="Скачивание...")
        log.info(f"Загрузка сессии BatchID: {self.current_batch_id}")
        
        export_thread = threading.Thread(target=self.run_export_logic, daemon=True)
        export_thread.start()

    def run_export_logic(self):
        output_file = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title=f"Сохранить результаты BatchID {self.current_batch_id}"
        )
        
        if not output_file:
            log.warning("Скачивание отменено пользователем.")
            self.master.after(0, lambda: self.export_button.config(state=tk.NORMAL, text="Скачать текущие дела"))
            return

        try:
            data_to_export = sqlite.get_case_participants(self.current_batch_id) 
            
            if not data_to_export:
                self.master.after(0, lambda: messagebox.showinfo("Скачивание", "Нет данных для скачивания в текущем пакете."))
                return
                
            dataloader.write_data_to_excel(data_to_export, output_file)
            
            self.master.after(0, lambda: messagebox.showinfo("Скачать", f"Данные успешно скачаны в {os.path.basename(output_file)}."))
            
        except Exception as e:
            error_msg = f"Ошибка при скачивании: {e}"
            log.error(error_msg)
            self.master.after(0, lambda: messagebox.showerror("Ошибка скачивания", error_msg))
            
        finally:
            self.master.after(0, lambda: self.export_button.config(state=tk.NORMAL, text="Скачать текущий пакет"))

    def check_can_process(self):
        if self.excel_path and os.path.exists(self.excel_path):
             self.process_button.config(state=tk.NORMAL)
        else:
             self.process_button.config(state=tk.DISABLED)


    def start_processing_thread(self):

        if not self.excel_path or not os.path.exists(self.excel_path):
            messagebox.showerror("Ошибка", "Необходимо выбрать файл Excel.")
            self.check_can_process()
            return

        self.process_button.config(state=tk.DISABLED, text="Обработка...")
        self.select_button.config(state=tk.DISABLED)

        self.stop_event.clear()
        self.stop_button.config(state=tk.NORMAL, text="Остановка")
        
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Инициализация...")
        
        log.info("Запуск подачи")
        
        self.processing_thread = threading.Thread(target=self.run_main_logic, daemon=True)
        self.processing_thread.start()
    
    def start_progress_update(self):
        self.progress_thread_running = True 
        self.progress_thread = threading.Thread(target=self.run_progress_update_logic, daemon=True)
        self.progress_thread.start()

    def run_progress_update_logic(self):
        while self.progress_thread_running and not self.stop_event.is_set():
            if self.current_batch_id:
                try:

                    processed_count, total_count = sqlite.get_batch_progress(self.current_batch_id) 
                    
                    if total_count > 0:
                        progress_value = int((processed_count / total_count) * 100)
                        
                        self.master.after(0, lambda: self.update_progress_gui(progress_value, processed_count, total_count))
                    
                except Exception as e:
                    log.error(f"Ошибка при обновлении прогресса: {e}")

            time.sleep(5)

    def update_progress_gui(self, value, processed, total):
        self.progress_bar['value'] = value
        self.progress_label.config(text=f"Обработано: {processed} из {total} ({value}%)")
        
    def run_main_logic(self):
        try:
            sqlite.check_and_initialize_db()
            batch_id = dataloader.load_excel_to_db(self.excel_path)
            self.current_batch_id = batch_id

            self.start_progress_update()
            
            case_processor.start_processing(batch_id, self.stop_event)
            self.master.after(0, lambda: messagebox.showinfo("Готово", "Обработка всех дел успешно завершена."))

        except Exception as e:
            error_msg = f"Ошибка: {e}"
            log.error(error_msg)
            self.master.after(0, lambda: messagebox.showerror("Ошибка", error_msg))
            
        finally:
            self.progress_thread_running = False
            self.master.after(0, self.finish_processing)
            self.master.after(0, lambda: self.export_button.config(state=tk.NORMAL, text="Скачать текущий пакет"))

    def finish_processing(self):
        self.stop_button.config(state=tk.DISABLED, text="Остановка")
        self.process_button.config(state=tk.NORMAL, text="Начать подачу")
        self.select_button.config(state=tk.NORMAL)
        if self.current_batch_id:
            try:
                 processed_count, total_count = sqlite.get_batch_progress(self.current_batch_id)
                 if processed_count == total_count and total_count > 0:
                      self.update_progress_gui(100, processed_count, total_count)
                 elif total_count > 0:
                      self.update_progress_gui(100, processed_count, total_count)
            except:
                 pass
        
        self.check_can_process()