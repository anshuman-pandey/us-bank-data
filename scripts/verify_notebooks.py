"""Execute the checked-in notebooks in a fresh kernel using this Python interpreter."""
import tempfile
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='banksonsale-notebooks-') as directory:
    for path in sorted((root/'notebooks').glob('*.ipynb')):
        notebook=nbformat.read(path,as_version=4)
        nbformat.validate(notebook)
        # The release environment installs its own kernelspec, preventing accidental use of a user's kernel.
        NotebookClient(notebook,timeout=90,kernel_name='banksonsale-launch',resources={'metadata':{'path':directory}}).execute()
        print(f'Passed: {path.name}')
