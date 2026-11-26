import math
import sys
import time
from PyQt5.QtCore import Qt, QEvent, QPointF, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPolygonF, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QTableWidgetItem,
    QFileDialog,
    QHeaderView,
)
from interface import Ui_MainWindow
from algorithms import (
    step_by_step_line,
    dda_line,
    bresenham_line,
    bresenham_circle,
    castle_pitteway_line,
    wu_line,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.pixels = {}
        self.ideal_overlay = None
        self.last_trace = []

        self.cell_size = 24
        self.min_cell_size = 6
        self.max_cell_size = 64
        self.offset_x = 0.0
        self.offset_y = 0.0
        self._dragging = False
        self._last_mouse_pos = None
        self._pick_toggle = 0

        self.ui.labelCanvas.setMouseTracking(True)
        self.ui.labelCanvas.installEventFilter(self)

        self._setup_tables()
        self._connect_signals()
        self._update_parameter_labels(self.ui.comboAlgorithm.currentIndex())
        self.draw_current_primitive()

    def _setup_tables(self) -> None:
        self.ui.tableTrace.setColumnCount(5)
        self.ui.tableTrace.setHorizontalHeaderLabels(["Шаг", "X", "Y", "Alpha", "Вычисления"])
        self.ui.tableTrace.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

        self.ui.tableTiming.setColumnCount(4)
        self.ui.tableTiming.setHorizontalHeaderLabels([
            "Алгоритм",
            "Среднее время (мкс)",
            "Суммарно за 1000 запусков (мс)",
            "Пикселей",
        ])
        self.ui.tableTiming.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def _connect_signals(self) -> None:
        self.ui.comboAlgorithm.currentIndexChanged.connect(self._update_parameter_labels)
        self.ui.btnDraw.clicked.connect(self.draw_current_primitive)
        self.ui.btnClear.clicked.connect(self.clear_canvas)
        self.ui.btnResetView.clicked.connect(self.reset_view)
        self.ui.sliderZoom.valueChanged.connect(self._on_zoom_changed)

        self.ui.chkShowGrid.toggled.connect(self.render_canvas)
        self.ui.chkShowLabels.toggled.connect(self.render_canvas)
        self.ui.chkShowAlphaValues.toggled.connect(self.render_canvas)
        self.ui.chkShowIdeal.toggled.connect(self.render_canvas)

        self.ui.btnExportTrace.clicked.connect(self.export_trace)
        self.ui.btnMeasureAll.clicked.connect(self.measure_all_algorithms)

    def _update_parameter_labels(self, index: int) -> None:
        if index == 3:
            self.ui.labelX1.setText("Xc (центр):")
            self.ui.labelY1.setText("Yc (центр):")
            self.ui.labelX2.setText("Радиус R:")
            self.ui.labelY2.setVisible(False)
            self.ui.spinY2.setVisible(False)
        else:
            self.ui.labelX1.setText("X1:")
            self.ui.labelY1.setText("Y1:")
            self.ui.labelX2.setText("X2:")
            self.ui.labelY2.setText("Y2:")
            self.ui.labelY2.setVisible(True)
            self.ui.spinY2.setVisible(True)

    def _on_zoom_changed(self, value: int) -> None:
        self.cell_size = value
        self.ui.labelZoomValue.setText(f"{value} px")
        self.render_canvas()

    def reset_view(self) -> None:
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.ui.sliderZoom.setValue(24)
        self.render_canvas()

    def world_to_screen(self, wx: float, wy: float) -> QPointF:
        cx = self.ui.labelCanvas.width() / 2.0 + self.offset_x
        cy = self.ui.labelCanvas.height() / 2.0 + self.offset_y
        return QPointF(cx + wx * self.cell_size, cy - wy * self.cell_size)

    def screen_to_world(self, sx: float, sy: float):
        cx = self.ui.labelCanvas.width() / 2.0 + self.offset_x
        cy = self.ui.labelCanvas.height() / 2.0 + self.offset_y
        wx = (sx - cx) / self.cell_size
        wy = (cy - sy) / self.cell_size
        return wx, wy

    def screen_to_cell(self, sx: float, sy: float):
        wx, wy = self.screen_to_world(sx, sy)
        return math.floor(wx + 0.5), math.floor(wy + 0.5)

    def eventFilter(self, obj, event) -> bool:
        if obj is not self.ui.labelCanvas:
            return super().eventFilter(obj, event)

        etype = event.type()
        if etype == QEvent.Resize:
            self.render_canvas()
            return False
        if etype == QEvent.Wheel:
            self._handle_wheel(event)
            return True
        if etype == QEvent.MouseButtonPress:
            self._handle_mouse_press(event)
            return True
        if etype == QEvent.MouseMove:
            self._handle_mouse_move(event)
            return True
        if etype == QEvent.MouseButtonRelease:
            self._handle_mouse_release(event)
            return True
        return super().eventFilter(obj, event)

    def _handle_wheel(self, event) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return
        step = 2 if self.cell_size < 20 else 4
        new_size = max(self.min_cell_size, min(self.max_cell_size, self.cell_size + (step if delta > 0 else -step)))
        if new_size == self.cell_size:
            return

        mx = event.pos().x()
        my = event.pos().y()
        wx, wy = self.screen_to_world(mx, my)
        self.cell_size = new_size
        self.offset_x = mx - self.ui.labelCanvas.width() / 2.0 - wx * self.cell_size
        self.offset_y = my - self.ui.labelCanvas.height() / 2.0 + wy * self.cell_size

        self.ui.sliderZoom.blockSignals(True)
        self.ui.sliderZoom.setValue(self.cell_size)
        self.ui.sliderZoom.blockSignals(False)
        self.ui.labelZoomValue.setText(f"{self.cell_size} px")
        self.render_canvas()

    def _handle_mouse_press(self, event) -> None:
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            self._dragging = True
            self._last_mouse_pos = event.pos()
            self.ui.labelCanvas.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.RightButton:
            cx, cy = self.screen_to_cell(event.pos().x(), event.pos().y())
            if self.ui.comboAlgorithm.currentIndex() == 3:
                self.ui.spinX1.setValue(cx)
                self.ui.spinY1.setValue(cy)
                self.draw_current_primitive()
            else:
                if self._pick_toggle == 0:
                    self.ui.spinX1.setValue(cx)
                    self.ui.spinY1.setValue(cy)
                else:
                    self.ui.spinX2.setValue(cx)
                    self.ui.spinY2.setValue(cy)
                    self.draw_current_primitive()
                self._pick_toggle = 1 - self._pick_toggle

    def _handle_mouse_move(self, event) -> None:
        if self._dragging and self._last_mouse_pos is not None:
            dx = event.pos().x() - self._last_mouse_pos.x()
            dy = event.pos().y() - self._last_mouse_pos.y()
            self.offset_x += dx
            self.offset_y += dy
            self._last_mouse_pos = event.pos()
            self.render_canvas()

        cx, cy = self.screen_to_cell(event.pos().x(), event.pos().y())
        alpha = self.pixels.get((cx, cy), 0.0)
        self.ui.labelCursorCoord.setText(f"Курсор: ({cx}, {cy}) | Alpha: {alpha:.2f}")

    def _handle_mouse_release(self, event) -> None:
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            self._dragging = False
            self._last_mouse_pos = None
            self.ui.labelCanvas.setCursor(Qt.ArrowCursor)

    def clear_canvas(self) -> None:
        self.pixels.clear()
        self.ideal_overlay = None
        self.last_trace = []
        self.ui.tableTrace.setRowCount(0)
        self.ui.labelTime.setText("Время: —")
        self.ui.labelPixelCount.setText("Закрашено пикселей: 0")
        self.render_canvas()

    def draw_current_primitive(self) -> None:
        if not self.ui.chkAccumulate.isChecked():
            self.pixels.clear()

        idx = self.ui.comboAlgorithm.currentIndex()
        x1 = self.ui.spinX1.value()
        y1 = self.ui.spinY1.value()
        x2 = self.ui.spinX2.value()
        y2 = self.ui.spinY2.value()

        t0 = time.perf_counter()
        if idx == 0:
            pts, _ = step_by_step_line(x1, y1, x2, y2, with_trace=False)
            t1 = time.perf_counter()
            _, trace = step_by_step_line(x1, y1, x2, y2, with_trace=True)
            self.ideal_overlay = ("line", x1, y1, x2, y2)
        elif idx == 1:
            pts, _ = dda_line(x1, y1, x2, y2, with_trace=False)
            t1 = time.perf_counter()
            _, trace = dda_line(x1, y1, x2, y2, with_trace=True)
            self.ideal_overlay = ("line", x1, y1, x2, y2)
        elif idx == 2:
            pts, _ = bresenham_line(x1, y1, x2, y2, with_trace=False)
            t1 = time.perf_counter()
            _, trace = bresenham_line(x1, y1, x2, y2, with_trace=True)
            self.ideal_overlay = ("line", x1, y1, x2, y2)
        elif idx == 3:
            r = abs(x2)
            pts, _ = bresenham_circle(x1, y1, r, with_trace=False)
            t1 = time.perf_counter()
            _, trace = bresenham_circle(x1, y1, r, with_trace=True)
            self.ideal_overlay = ("circle", x1, y1, r)
        elif idx == 4:
            pts, _ = castle_pitteway_line(x1, y1, x2, y2, with_trace=False)
            t1 = time.perf_counter()
            _, trace = castle_pitteway_line(x1, y1, x2, y2, with_trace=True)
            self.ideal_overlay = ("line", x1, y1, x2, y2)
        else:
            pts, _ = wu_line(x1, y1, x2, y2, with_trace=False)
            t1 = time.perf_counter()
            _, trace = wu_line(x1, y1, x2, y2, with_trace=True)
            self.ideal_overlay = ("line", x1, y1, x2, y2)

        for px, py, alpha in pts:
            if alpha > self.pixels.get((px, py), 0.0):
                self.pixels[(px, py)] = alpha

        elapsed_us = (t1 - t0) * 1_000_000.0
        self.ui.labelTime.setText(f"Время: {elapsed_us:.2f} мкс ({(t1 - t0) * 1000.0:.5f} мс)")
        self.ui.labelPixelCount.setText(f"Закрашено пикселей: {len(self.pixels)}")

        self._populate_trace_table(trace)
        self.render_canvas()

    def _populate_trace_table(self, trace) -> None:
        self.last_trace = trace
        self.ui.tableTrace.setRowCount(len(trace))
        for row_idx, (step, x, y, alpha, desc) in enumerate(trace):
            self.ui.tableTrace.setItem(row_idx, 0, QTableWidgetItem(str(step)))
            self.ui.tableTrace.setItem(row_idx, 1, QTableWidgetItem(str(x)))
            self.ui.tableTrace.setItem(row_idx, 2, QTableWidgetItem(str(y)))
            self.ui.tableTrace.setItem(row_idx, 3, QTableWidgetItem(f"{alpha:.4f}"))
            self.ui.tableTrace.setItem(row_idx, 4, QTableWidgetItem(desc))

    def export_trace(self) -> None:
        if not self.last_trace:
            QMessageBox.information(self, "Экспорт", "Нет данных для сохранения.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить протокол", "trace.txt", "Text Files (*.txt)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"Алгоритм: {self.ui.comboAlgorithm.currentText()}\n")
            fh.write("Шаг\tX\tY\tAlpha\tВычисления\n")
            for step, x, y, alpha, desc in self.last_trace:
                fh.write(f"{step}\t{x}\t{y}\t{alpha:.4f}\t{desc}\n")
        QMessageBox.information(self, "Экспорт", "Протокол вычислений сохранен.")

    def measure_all_algorithms(self) -> None:
        x1 = self.ui.spinX1.value()
        y1 = self.ui.spinY1.value()
        x2 = self.ui.spinX2.value()
        y2 = self.ui.spinY2.value()
        r = max(1, abs(x2))
        runs = 1000

        tests = [
            ("Пошаговый алгоритм", lambda: step_by_step_line(x1, y1, x2, y2)),
            ("Алгоритм ЦДА", lambda: dda_line(x1, y1, x2, y2)),
            ("Алгоритм Брезенхема (отрезок)", lambda: bresenham_line(x1, y1, x2, y2)),
            (f"Алгоритм Брезенхема (окружность R={r})", lambda: bresenham_circle(x1, y1, r)),
            ("Алгоритм Кастла-Питвея (отрезок)", lambda: castle_pitteway_line(x1, y1, x2, y2)),
            ("Алгоритм Ву (сглаживание)", lambda: wu_line(x1, y1, x2, y2)),
        ]

        self.ui.tableTiming.setRowCount(len(tests))
        for row_idx, (name, fn) in enumerate(tests):
            pts, _ = fn()
            t0 = time.perf_counter()
            for _ in range(runs):
                fn()
            elapsed = time.perf_counter() - t0
            avg_us = (elapsed / runs) * 1_000_000.0
            total_ms = elapsed * 1000.0

            self.ui.tableTiming.setItem(row_idx, 0, QTableWidgetItem(name))
            self.ui.tableTiming.setItem(row_idx, 1, QTableWidgetItem(f"{avg_us:.2f}"))
            self.ui.tableTiming.setItem(row_idx, 2, QTableWidgetItem(f"{total_ms:.3f}"))
            self.ui.tableTiming.setItem(row_idx, 3, QTableWidgetItem(str(len(set((p[0], p[1]) for p in pts)))))

    def _tick_step(self) -> int:
        if self.cell_size >= 26:
            return 1
        if self.cell_size >= 14:
            return 2
        if self.cell_size >= 8:
            return 5
        return 10

    def render_canvas(self) -> None:
        w = max(1, self.ui.labelCanvas.width())
        h = max(1, self.ui.labelCanvas.height())
        pixmap = QPixmap(w, h)
        pixmap.fill(QColor(252, 253, 255))

        painter = QPainter(pixmap)
        cs = self.cell_size
        cx = w / 2.0 + self.offset_x
        cy = h / 2.0 + self.offset_y
        half = cs / 2.0

        min_wx = math.floor((0 - cx) / cs) - 1
        max_wx = math.ceil((w - cx) / cs) + 1
        min_wy = math.floor((cy - h) / cs) - 1
        max_wy = math.ceil(cy / cs) + 1

        show_alpha = self.ui.chkShowAlphaValues.isChecked() and cs >= 26
        if show_alpha:
            painter.setFont(QFont("Consolas", 7))

        for (wx, wy), intensity in self.pixels.items():
            if min_wx <= wx <= max_wx and min_wy <= wy <= max_wy and intensity > 0.0:
                sx = cx + wx * cs - half
                sy = cy - wy * cs - half
                alpha = int(round(intensity * 255))
                painter.fillRect(QRectF(sx, sy, cs, cs), QColor(28, 92, 214, alpha))
                if show_alpha:
                    text_color = QColor(255, 255, 255) if intensity > 0.55 else QColor(20, 35, 65)
                    painter.setPen(text_color)
                    painter.drawText(QRectF(sx, sy, cs, cs), Qt.AlignCenter, f"{intensity:.2f}")

        if self.ui.chkShowGrid.isChecked() and cs >= 6:
            painter.setPen(QPen(QColor(218, 224, 234), 1))
            for gx in range(min_wx, max_wx + 2):
                sx = cx + (gx - 0.5) * cs
                painter.drawLine(QPointF(sx, 0), QPointF(sx, h))
            for gy in range(min_wy, max_wy + 2):
                sy = cy - (gy - 0.5) * cs
                painter.drawLine(QPointF(0, sy), QPointF(w, sy))

        painter.setPen(QPen(QColor(40, 48, 64), 2))
        painter.drawLine(QPointF(0, cy), QPointF(w, cy))
        painter.drawLine(QPointF(cx, 0), QPointF(cx, h))

        painter.setBrush(QColor(40, 48, 64))
        painter.drawPolygon(QPolygonF([
            QPointF(w - 2, cy),
            QPointF(w - 12, cy - 5),
            QPointF(w - 12, cy + 5),
        ]))
        painter.drawPolygon(QPolygonF([
            QPointF(cx, 2),
            QPointF(cx - 5, 12),
            QPointF(cx + 5, 12),
        ]))

        if self.ui.chkShowLabels.isChecked():
            painter.setFont(QFont("Segoe UI", 8))
            step = self._tick_step()
            painter.setPen(QColor(55, 65, 81))

            start_x = (min_wx // step) * step
            for wx in range(start_x, max_wx + 1, step):
                sx = cx + wx * cs
                painter.drawLine(QPointF(sx, cy - 3), QPointF(sx, cy + 3))
                if wx != 0:
                    painter.drawText(QRectF(sx - 18, cy + 5, 36, 16), Qt.AlignHCenter | Qt.AlignTop, str(wx))

            start_y = (min_wy // step) * step
            for wy in range(start_y, max_wy + 1, step):
                sy = cy - wy * cs
                painter.drawLine(QPointF(cx - 3, sy), QPointF(cx + 3, sy))
                if wy != 0:
                    painter.drawText(QRectF(cx - 38, sy - 8, 32, 16), Qt.AlignRight | Qt.AlignVCenter, str(wy))

            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(QRectF(cx + 4, cy + 4, 24, 16), Qt.AlignLeft | Qt.AlignTop, "0")
            painter.drawText(QRectF(w - 24, cy - 22, 18, 18), Qt.AlignCenter, "X")
            painter.drawText(QRectF(cx + 8, 6, 18, 18), Qt.AlignCenter, "Y")

        if self.ui.chkShowIdeal.isChecked() and self.ideal_overlay is not None:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setPen(QPen(QColor(220, 38, 38, 190), 1.5, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            if self.ideal_overlay[0] == "line":
                _, x1, y1, x2, y2 = self.ideal_overlay
                painter.drawLine(self.world_to_screen(x1, y1), self.world_to_screen(x2, y2))
            elif self.ideal_overlay[0] == "circle":
                _, xc, yc, r = self.ideal_overlay
                center = self.world_to_screen(xc, yc)
                r_px = abs(r) * cs
                painter.drawEllipse(center, r_px, r_px)
            painter.restore()

        painter.end()
        self.ui.labelCanvas.setPixmap(pixmap)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
