import sys
import time
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLabel, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

from interface import Ui_MainWindow
from buffer_wrapper import BufferWrapper
from algorithms import ImageAlgorithms


class WorkerThread(QThread):
    progress = pyqtSignal(int)
    finished_ok = pyqtSignal(object, float)
    failed = pyqtSignal(str)

    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args

    def run(self):
        try:
            t0 = time.perf_counter()
            result = self.func(*self.args, progress_callback=self.progress.emit)
            elapsed = time.perf_counter() - t0
            self.finished_ok.emit(result, elapsed)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.original_buffer = None
        self.current_buffer = None
        self.worker = None
        self.param1_scale = 1.0

        self.ui.btnLoad.clicked.connect(self.load_image)
        self.ui.btnSave.clicked.connect(self.save_image)
        self.ui.btnProcess.clicked.connect(self.process_image)
        self.ui.btnReset.clicked.connect(self.reset_image)
        self.ui.comboAlgo.currentIndexChanged.connect(self.update_param_controls)

        self.ui.sliderParam1.valueChanged.connect(self.on_slider1_changed)
        self.ui.spinParam1.valueChanged.connect(self.on_spin1_changed)
        self.ui.sliderParam2.valueChanged.connect(self.ui.spinParam2.setValue)
        self.ui.spinParam2.valueChanged.connect(self.ui.sliderParam2.setValue)

        self.update_param_controls(self.ui.comboAlgo.currentIndex())

    def on_slider1_changed(self, value: int):
        self.ui.spinParam1.blockSignals(True)
        self.ui.spinParam1.setValue(value / self.param1_scale)
        self.ui.spinParam1.blockSignals(False)

    def on_spin1_changed(self, value: float):
        self.ui.sliderParam1.blockSignals(True)
        self.ui.sliderParam1.setValue(int(round(value * self.param1_scale)))
        self.ui.sliderParam1.blockSignals(False)

    def configure_param1(self, title: str, min_v: float, max_v: float, default_v: float, step: float, decimals: int, scale: float):
        self.param1_scale = scale
        self.ui.labelParam1.setText(title)
        self.ui.spinParam1.blockSignals(True)
        self.ui.sliderParam1.blockSignals(True)

        self.ui.spinParam1.setDecimals(decimals)
        self.ui.spinParam1.setSingleStep(step)
        self.ui.spinParam1.setRange(min_v, max_v)
        self.ui.spinParam1.setValue(default_v)

        self.ui.sliderParam1.setRange(int(round(min_v * scale)), int(round(max_v * scale)))
        self.ui.sliderParam1.setValue(int(round(default_v * scale)))

        self.ui.spinParam1.blockSignals(False)
        self.ui.sliderParam1.blockSignals(False)

    def set_param1_visible(self, visible: bool):
        self.ui.labelParam1.setVisible(visible)
        self.ui.sliderParam1.setVisible(visible)
        self.ui.spinParam1.setVisible(visible)

    def set_param2_visible(self, visible: bool):
        self.ui.labelParam2.setVisible(visible)
        self.ui.sliderParam2.setVisible(visible)
        self.ui.spinParam2.setVisible(visible)

    def set_edge_visible(self, visible: bool):
        self.ui.labelEdgeMode.setVisible(visible)
        self.ui.comboEdgeMode.setVisible(visible)

    def update_param_controls(self, idx: int):
        if idx == 0:
            self.ui.groupParams.setVisible(True)
            self.set_param1_visible(True)
            self.set_param2_visible(False)
            self.set_edge_visible(False)
            self.configure_param1("Смещение яркости (c):", -255.0, 255.0, 40.0, 1.0, 0, 1.0)
        elif idx == 1:
            self.ui.groupParams.setVisible(True)
            self.set_param1_visible(True)
            self.set_param2_visible(False)
            self.set_edge_visible(False)
            self.configure_param1("Коэффициент контраста (k):", 0.1, 4.0, 1.5, 0.05, 2, 100.0)
        elif idx == 3:
            self.ui.groupParams.setVisible(True)
            self.set_param1_visible(True)
            self.set_param2_visible(False)
            self.set_edge_visible(False)
            self.configure_param1("Показатель гаммы:", 0.1, 5.0, 0.5, 0.05, 2, 100.0)
        elif idx == 4:
            self.ui.groupParams.setVisible(True)
            self.set_param1_visible(True)
            self.set_param2_visible(False)
            self.set_edge_visible(False)
            self.configure_param1("Масштаб (gain):", 0.2, 2.0, 1.0, 0.05, 2, 100.0)
        elif idx == 8:
            self.ui.groupParams.setVisible(True)
            self.set_param1_visible(True)
            self.set_param2_visible(True)
            self.set_edge_visible(True)
            self.configure_param1("Порог отсечения (Clip Limit):", 1.0, 10.0, 2.5, 0.1, 1, 10.0)
        else:
            self.ui.groupParams.setVisible(False)

    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Открыть изображение", "", "Изображения (*.png *.jpg *.jpeg *.bmp *.tif)"
        )
        if not file_name:
            return
        img = QImage(file_name)
        if img.isNull():
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить изображение.")
            return
        img = img.convertToFormat(QImage.Format_RGB888)
        w, h = img.width(), img.height()
        bpl = img.bytesPerLine()
        ptr = img.bits()
        ptr.setsize(h * bpl)
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, bpl))[:, : w * 3].reshape((h, w, 3)).copy()

        self.original_buffer = BufferWrapper(arr)
        self.current_buffer = BufferWrapper(arr.copy())
        self.ui.progressBar.setValue(0)
        self.ui.labelStatus.setText(f"Загружено: {w}x{h} px")
        self.refresh_views()

    def save_image(self):
        if self.current_buffer is None:
            return
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Сохранить результат", "result.png", "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)"
        )
        if not file_name:
            return
        q_img = self.buffer_to_qimage(self.current_buffer)
        if not q_img.save(file_name):
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить изображение.")
        else:
            self.ui.labelStatus.setText(f"Сохранено: {file_name}")

    @staticmethod
    def buffer_to_qimage(buffer: BufferWrapper) -> QImage:
        u8 = np.ascontiguousarray(buffer.to_uint8())
        h, w = u8.shape[:2]
        if u8.ndim == 2:
            return QImage(u8.data, w, h, w, QImage.Format_Grayscale8).copy()
        return QImage(u8.data, w, h, w * 3, QImage.Format_RGB888).copy()

    def show_image(self, buffer: BufferWrapper, label: QLabel):
        q_img = self.buffer_to_qimage(buffer)
        target_size = label.size()
        if target_size.width() <= 1 or target_size.height() <= 1:
            return
        pixmap = QPixmap.fromImage(q_img).scaled(
            target_size.width(),
            target_size.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        label.setPixmap(pixmap)

    def refresh_views(self):
        if self.original_buffer is not None:
            self.show_image(self.original_buffer, self.ui.lblOrig)
        if self.current_buffer is not None:
            self.show_image(self.current_buffer, self.ui.lblProcessed)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_views()

    def set_controls_enabled(self, enabled: bool):
        self.ui.btnLoad.setEnabled(enabled)
        self.ui.btnSave.setEnabled(enabled)
        self.ui.btnProcess.setEnabled(enabled)
        self.ui.btnReset.setEnabled(enabled)
        self.ui.comboAlgo.setEnabled(enabled)
        self.ui.groupParams.setEnabled(enabled)

    def process_image(self):
        if self.original_buffer is None:
            return
        if self.worker is not None and self.worker.isRunning():
            return

        idx = self.ui.comboAlgo.currentIndex()
        p1 = self.ui.spinParam1.value()
        p2 = self.ui.spinParam2.value()
        edge_mode = "reflect" if self.ui.comboEdgeMode.currentIndex() == 0 else "clamp"

        if idx == 0:
            func, args = ImageAlgorithms.add_brightness, (self.original_buffer, p1)
        elif idx == 1:
            func, args = ImageAlgorithms.multiply_contrast, (self.original_buffer, p1)
        elif idx == 2:
            func, args = ImageAlgorithms.negative, (self.original_buffer,)
        elif idx == 3:
            func, args = ImageAlgorithms.gamma_correction, (self.original_buffer, p1)
        elif idx == 4:
            func, args = ImageAlgorithms.log_transform, (self.original_buffer, p1)
        elif idx == 5:
            func, args = ImageAlgorithms.linear_contrast, (self.original_buffer,)
        elif idx == 6:
            func, args = ImageAlgorithms.histogram_equalization_rgb, (self.original_buffer,)
        elif idx == 7:
            func, args = ImageAlgorithms.histogram_equalization_hsv, (self.original_buffer,)
        else:
            func, args = ImageAlgorithms.clahe, (self.original_buffer, p1, p2, edge_mode)

        self.set_controls_enabled(False)
        self.ui.progressBar.setValue(0)
        self.ui.labelStatus.setText("Обработка...")

        self.worker = WorkerThread(func, *args)
        self.worker.progress.connect(self.ui.progressBar.setValue)
        self.worker.finished_ok.connect(self.on_processing_done)
        self.worker.failed.connect(self.on_processing_error)
        self.worker.start()

    def on_processing_done(self, result_buffer: BufferWrapper, elapsed: float):
        self.current_buffer = result_buffer
        self.refresh_views()
        self.set_controls_enabled(True)
        self.ui.progressBar.setValue(100)
        self.ui.labelStatus.setText(f"Готово за {elapsed * 1000:.1f} мс")

    def on_processing_error(self, message: str):
        self.set_controls_enabled(True)
        self.ui.progressBar.setValue(0)
        self.ui.labelStatus.setText("Ошибка обработки")
        QMessageBox.critical(self, "Ошибка", message)

    def reset_image(self):
        if self.original_buffer is not None:
            self.current_buffer = BufferWrapper(self.original_buffer.data.copy())
            self.ui.progressBar.setValue(0)
            self.ui.labelStatus.setText("Изображение сброшено")
            self.refresh_views()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
