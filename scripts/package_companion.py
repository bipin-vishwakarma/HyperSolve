"""Package the same reviewed companion folder alongside the Windows app."""
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hypersolve.__version__ import __version__

root=Path(__file__).resolve().parents[1]
assert (root/'extension/parser.js').read_bytes()==(root/'hypersolve/parser/dom_parser.js').read_bytes(), 'Shared parser copies differ'
target=root/'dist/HyperSolve/browser-extension'
shutil.copytree(root/'extension',target,dirs_exist_ok=True)
(root/'dist_installer').mkdir(exist_ok=True)
shutil.make_archive(str(root/f'dist_installer/HyperSolve-Browser-Companion-v{__version__}'),'zip',root/'extension')
