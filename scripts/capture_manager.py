"""Capture native manager at normal and minimum sizes with labelled fixture sessions."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import sys
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PyQt6.QtWidgets import QApplication
from hypersolve.desktop.dashboard_window import HyperSolveDashboard
from hypersolve.companion.agents import AgentManager

app=QApplication([])
window=HyperSolveDashboard(auto_scan=False)
manager=AgentManager()
manager.hello('fixture','Chrome')
for index,title in enumerate(('Practice assessment · Biology','Revision questions · Statistics'),1):
    manager.detect('fixture',{'id':str(index),'tab':index,'url':f'https://example.test/quiz?id={index}','title':title,'visible':5,'total':20})
manager.control('fixture','1','approve')
manager.progress('fixture','1','harvesting','Reading page 2 of the practice quiz',10)
window.companion=SimpleNamespace(manager=manager)
window.agent_timer.timeout.emit()
window.setWindowTitle('HyperSolve — local fixture preview')
output=Path(__file__).resolve().parents[1]/'scratch/review'
output.mkdir(parents=True,exist_ok=True)
for width,height in ((1160,780),(860,620)):
    window.resize(width,height);window.show();app.processEvents()
    assert window.grab().save(str(output/f'manager-{width}.png'))
window.tray.hide()
manager.close()
window.deleteLater()
