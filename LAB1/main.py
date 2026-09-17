import sys
from PyQt5.QtWidgets import QApplication, QWidget, QColorDialog, QMessageBox
from PyQt5.QtGui import QColor
from interface import Ui_ColorConverterUI
import funct as cc

class ColorConverterApp(QWidget, Ui_ColorConverterUI):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.updating = False
        self.setup_connections()
        self.set_color_from_rgb(255, 255, 255)
        
    def setup_connections(self):
        self.color_button.clicked.connect(self.choose_color)
        self.help_button.clicked.connect(self.show_help)
        
        rgb_components = [
            (self.slider_R, self.spinbox_R),
            (self.slider_G, self.spinbox_G),
            (self.slider_B, self.spinbox_B)
        ]
        for sl, sp in rgb_components:
            sl.valueChanged.connect(sp.setValue)
            sp.valueChanged.connect(sl.setValue)
            sl.valueChanged.connect(self.update_from_rgb)

        cmyk_components = [
            (self.slider_C, self.spinbox_C),
            (self.slider_M, self.spinbox_M),
            (self.slider_Y, self.spinbox_Y),
            (self.slider_K, self.spinbox_K)
        ]
        for sl, sp in cmyk_components:
            sl.valueChanged.connect(sp.setValue)
            sp.valueChanged.connect(sl.setValue)
            sl.valueChanged.connect(self.update_from_cmyk)

        lab_components = [
            (self.slider_L, self.spinbox_L),
            (self.slider_A, self.spinbox_A),
            (self.slider_B_lab, self.spinbox_B_lab)
        ]
        for sl, sp in lab_components:
            sl.valueChanged.connect(sp.setValue)
            sp.valueChanged.connect(sl.setValue)
            sl.valueChanged.connect(self.update_from_lab)

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.slider_R.value(), self.slider_G.value(), self.slider_B.value()), self)
        if color.isValid():
            self.set_color_from_rgb(color.red(), color.green(), color.blue())

    def show_help(self):
        QMessageBox.information(self, "Help Guide", 
            "Программа позволяет интерактивно менять цвет и наблюдать его составляющие в RGB, CMYK и LAB.\n"
            "Предупреждения о потере точности при выходе за границы цветового охвата показываются красным текстом.")

    def set_color_button_style(self, r, g, b):
        self.color_button.setStyleSheet(f"background-color: rgb({r}, {g}, {b}); border: 2px solid black;")

    def update_from_rgb(self):
        if self.updating: return
        self.updating = True
        self.warning_label.setText("")
        
        r, g, b = self.slider_R.value(), self.slider_G.value(), self.slider_B.value()
        c, m, y, k = cc.rgb_to_cmyk(r, g, b)
        l, a_lab, b_lab = cc.rgb_to_lab(r, g, b)
        
        self.update_cmyk_ui(c, m, y, k)
        self.update_lab_ui(l, a_lab, b_lab)
        self.set_color_button_style(r, g, b)
        self.updating = False

    def update_from_cmyk(self):
        if self.updating: return
        self.updating = True
        self.warning_label.setText("")
        
        c, m, y, k = self.slider_C.value(), self.slider_M.value(), self.slider_Y.value(), self.slider_K.value()
        
        r, g, b = cc.cmyk_to_rgb(c, m, y, k)
        l, a_lab, b_lab = cc.cmyk_to_lab(c, m, y, k)
        
        self.update_rgb_ui(r, g, b)
        self.update_lab_ui(l, a_lab, b_lab)
        self.set_color_button_style(r, g, b)
        self.updating = False

    def update_from_lab(self):
        if self.updating: return
        self.updating = True
        self.warning_label.setText("")
        
        l, a, b_lab = self.slider_L.value(), self.slider_A.value(), self.slider_B_lab.value()
        
        r, g, b, warning1 = cc.lab_to_rgb(l, a, b_lab)
        c, m, y, k, warning2 = cc.lab_to_cmyk(l, a, b_lab)
        
        if warning1 or warning2:
            self.warning_label.setText("Предупреждение: Обрезка значений (выход за границы цветового охвата RGB/CMYK)")
            
        self.update_rgb_ui(r, g, b)
        self.update_cmyk_ui(c, m, y, k)
        self.set_color_button_style(r, g, b)
        self.updating = False

    def set_color_from_rgb(self, r, g, b):
        if self.updating: return
        self.updating = True
        self.update_rgb_ui(r, g, b)
        self.updating = False
        self.update_from_rgb()

    def update_rgb_ui(self, r, g, b):
        self.slider_R.setValue(int(r))
        self.slider_G.setValue(int(g))
        self.slider_B.setValue(int(b))

    def update_cmyk_ui(self, c, m, y, k):
        self.slider_C.setValue(int(c))
        self.slider_M.setValue(int(m))
        self.slider_Y.setValue(int(y))
        self.slider_K.setValue(int(k))

    def update_lab_ui(self, l, a, b):
        self.slider_L.setValue(int(l))
        self.slider_A.setValue(int(a))
        self.slider_B_lab.setValue(int(b))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ColorConverterApp()
    window.show()
    sys.exit(app.exec_())