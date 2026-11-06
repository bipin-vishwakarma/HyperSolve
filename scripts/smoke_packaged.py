"""Verify the bundled GUI starts its manager without a source/Python dependency."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import requests

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='hypersolve-packaged-') as directory:
    endpoint=Path(directory)/'companion-endpoint.json'
    env={**os.environ,'HYPERSOLVE_DATA_DIR':directory,'LOCALAPPDATA':directory,
         'QT_QPA_PLATFORM':'offscreen','PATH':os.pathsep.join((os.path.join(os.environ['SystemRoot'],'System32'),os.environ['SystemRoot']))}
    process=subprocess.Popen([str(root/'dist/HyperSolve/HyperSolve.exe'),'--tray'],cwd=directory,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for _ in range(150):
            if process.poll() is not None:raise AssertionError(f'Packaged GUI exited early: {process.returncode}')
            if endpoint.exists():break
            time.sleep(.1)
        assert endpoint.exists(),'Packaged manager did not start'
        data=json.loads(endpoint.read_text())
        reply=requests.post(data['url'],json={'op':'hello','client':'packaged-smoke','browser':'Fixture'},headers={'Authorization':'Bearer '+data['token']},timeout=5)
        reply.raise_for_status()
        assert reply.json()['stats']=={'active':0,'waiting':0,'selected':0,'review':0}
        assert (root/'dist/HyperSolve/browser-extension/manifest.json').is_file()
        assert (root/'dist/HyperSolve/HyperSolveBridge.exe').is_file()
        print('PASS: bundled GUI starts from isolated directory and serves authenticated manager; companion and console bridge present.')
    finally:
        process.terminate()
        process.wait(timeout=8)
