"""Render the authored SVG mark into Windows icon resolutions."""
from io import BytesIO
from pathlib import Path
import sys
from PIL import Image
from PyQt6.QtCore import QBuffer, QIODevice, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

root = Path(__file__).resolve().parents[1]
app = QApplication.instance() or QApplication([])
image = QImage(256, 256, QImage.Format.Format_ARGB32)
image.fill(Qt.GlobalColor.transparent)
painter = QPainter(image)
QSvgRenderer(str(root / "hypersolve/assets/mark.svg")).render(painter)
painter.end()
buffer = QBuffer()
buffer.open(QIODevice.OpenModeFlag.ReadWrite)
image.save(buffer, "PNG")
bitmap = Image.open(BytesIO(bytes(buffer.data())))
bitmap.save(root / "hypersolve/assets/hypersolve.png")
(root / "extension/icons").mkdir(parents=True,exist_ok=True)
for size in (16,32,48,128):
    bitmap.resize((size,size),Image.Resampling.LANCZOS).save(root / f"extension/icons/icon{size}.png")
for target in (root / "hypersolve/assets/hypersolve.ico", root / "installer/hypersolve.ico"):
    bitmap.save(target, sizes=[(n, n) for n in (16, 20, 24, 32, 40, 48, 64, 128, 256)])
