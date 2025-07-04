from PyQt5 import QtWidgets, uic
import sys

FormClass, BaseClass = uic.loadUiType("t.ui")  # لود فایل UI و تبدیل به کلاس

class MyApp(BaseClass, FormClass):
    def __init__(self):
        super().__init__()
        self.setupUi(self)  # اینجا ویجت‌ها (مثل frame1 و frame2) تعریف می‌شن

        self.frame1.show()
        self.frame2.show()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
