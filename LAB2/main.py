import sys
import os
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QTableWidgetItem, QHeaderView
from interface import Ui_MainWindow
from functions import get_image_metadata

class ScannerThread(QThread):
    progress = pyqtSignal(int)
    result = pyqtSignal(dict)
    finished = pyqtSignal()

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.is_running = True
        self.is_paused = False

    def run(self):
        files_to_process = []
        for root, _, files in os.walk(self.folder_path):
            for file in files:
                files_to_process.append(os.path.join(root, file))

        total_files = len(files_to_process)
        if total_files == 0:
            self.finished.emit()
            return

        for i, file_path in enumerate(files_to_process):
            if not self.is_running:
                break

            while self.is_paused:
                self.msleep(50)
                if not self.is_running:
                    break

            if not self.is_running:
                break

            metadata = get_image_metadata(file_path)
            metadata["name"] = os.path.basename(file_path)
            
            self.result.emit(metadata)
            
            progress_pct = int(((i + 1) / total_files) * 100)
            self.progress.emit(progress_pct)

        self.finished.emit()

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.is_paused = False


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        self.tableWidget.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.tableWidget.verticalHeader().setDefaultSectionSize(25)
        
        header = self.tableWidget.horizontalHeader()
        
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        
        self.tableWidget.setColumnWidth(1, 90)
        self.tableWidget.setColumnWidth(2, 100)
        self.tableWidget.setColumnWidth(3, 110)
        self.tableWidget.setColumnWidth(4, 130)
        self.tableWidget.setColumnWidth(5, 110)
        
        self.scanner_thread = None

        self.btn_select_folder.clicked.connect(self.select_folder)
        self.btn_pause.clicked.connect(self.pause_scanning)
        self.btn_resume.clicked.connect(self.resume_scanning)

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "")
        if folder_path:
            self.start_scanning(folder_path)

    def start_scanning(self, folder_path):
        self.tableWidget.setUpdatesEnabled(False)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setUpdatesEnabled(True)
        
        self.progressBar.setValue(0)
        self.btn_select_folder.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_resume.setEnabled(False)

        self.scanner_thread = ScannerThread(folder_path)
        self.scanner_thread.progress.connect(self.progressBar.setValue)
        self.scanner_thread.result.connect(self.add_table_row)
        self.scanner_thread.finished.connect(self.scan_finished)
        self.scanner_thread.start()

    def pause_scanning(self):
        if self.scanner_thread:
            self.scanner_thread.pause()
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(True)

    def resume_scanning(self):
        if self.scanner_thread:
            self.scanner_thread.resume()
            self.btn_pause.setEnabled(True)
            self.btn_resume.setEnabled(False)

    def add_table_row(self, data):
        row_position = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_position)
        
        self.tableWidget.setItem(row_position, 0, QTableWidgetItem(data["name"]))
        self.tableWidget.setItem(row_position, 1, QTableWidgetItem(data["format"]))
        self.tableWidget.setItem(row_position, 2, QTableWidgetItem(data["compression"]))
        self.tableWidget.setItem(row_position, 3, QTableWidgetItem(data["size"]))
        self.tableWidget.setItem(row_position, 4, QTableWidgetItem(data["resolution"]))
        self.tableWidget.setItem(row_position, 5, QTableWidgetItem(data["color_depth"]))

    def scan_finished(self):
        self.btn_select_folder.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())