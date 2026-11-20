"""pytest version of test_notebook.ipynb, run as the last step of the image build.

The same checks as the notebook, as plain pytest tests:
  - test_import: every Python package in CHECKS imports, and most run
    one minimal API call
  - test_cli: every command-line tool in CHECKS is on $PATH and starts
  - test_functional: the geolab-gmt tools in FUNCTIONAL do real work (a
    TauP travel time, a GMT coastline map, a PyGMT figure, a lossless
    JPEG 2000 file)

All of the checks are shared with test_notebook.ipynb, which runs the
same lists through test_helpers.py: CHECKS section by section with
run_section(), and FUNCTIONAL with run_functional(). A check added to
one of these lists is tested in both. The test ids are the labels in the
notebook's summary table.

To run it on a built image:

    docker run --rm <image> python -m pytest -p no:cacheprovider -ra test_notebook.py
"""

import importlib
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

# ──────────────────────────────────────────────────────────────
# Package checks, shared with test_notebook.ipynb
# ──────────────────────────────────────────────────────────────
# CHECKS is the one list of packages and command-line tools to check.
# test_notebook.ipynb runs it section by section (run_section() in
# test_helpers.py), and test_import/test_cli below run all of it, so a
# package added here is tested in both. A check's section is the
# notebook heading it runs under; each section keeps the notebook's order.


@dataclass(frozen=True)
class Check:
    kind: str                          # 'py': import name, then smoke(module); 'cli': run name
    name: str                          # module to import, or command on $PATH
    smoke: Callable | None = None      # py: a minimal API call that raises on failure
    alias: str | None = None           # py: label, the conda/pip name where it differs
    version_flag: str = '--version'    # cli: argument to start it with
    section: str = ''                  # notebook heading, set by _section()

    @property
    def label(self):
        return self.alias or self.name


def _py(name, smoke=None, alias=None):
    return Check('py', name, smoke=smoke, alias=alias)


def _cli(name, version_flag='--version'):
    return Check('cli', name, version_flag=version_flag)


def _section(section, *checks):
    return [replace(check, section=section) for check in checks]


CHECKS = [
    *_section(
        'Cloud & storage',
        _cli('aws'),
        _py('awswrangler'),
        _py('boto3', lambda m: m.client('s3', region_name='us-east-1')),
        _py('fsspec', lambda m: m.filesystem('memory')),
        _py('obstore'),
        _py('s3fs', lambda m: m.S3FileSystem),
    ),
    *_section(
        'Geospatial',
        _py('cartopy.crs', lambda m: m.PlateCarree(), alias='cartopy'),
        _py('contextily'),
        _py('fiona', lambda m: m.supported_drivers),
        _py('folium', lambda m: m.Map(location=[0, 0], zoom_start=2)),
        _py('osgeo.gdal', lambda m: m.VersionInfo('RELEASE_NAME'), alias='gdal'),
        _py('ipyleaflet', lambda m: m.Map()),
        _py('lonboard'),
        _py('pyproj', lambda m: m.CRS('EPSG:4326')),
        _py('shapely.geometry', lambda m: m.Point(0, 0).buffer(1).area, alias='shapely'),
    ),
    *_section(
        'Core scientific stack',
        _py('numpy', lambda m: int(m.array([1, 2, 3]).sum())),
        _py('numba', lambda m: m.njit(lambda x: x + 1)(1)),
        _py('scipy.stats', lambda m: m.norm.cdf(0), alias='scipy'),
        _py('pandas', lambda m: m.DataFrame({'a': [1, 2]}).shape),
        _py('geopandas'),
        _py('matplotlib', lambda m: m.figure.Figure(), alias='matplotlib-base'),
        _py('xarray', lambda m: m.DataArray([1, 2, 3]).sum().item()),
        _py('netCDF4', alias='netcdf4'),
        _py('h5py'),
        _py('h5netcdf'),
        _py('pyarrow', lambda m: m.array([1, 2, 3]).to_pylist()),
        _py('zarr', lambda m: m.zeros((3,), chunks=3, dtype='f4')),
        _py('virtualizarr'),
        _py('bottleneck', lambda m: m.nansum([1.0, 2.0, float('nan'), 3.0])),
        _py('flox'),
        _py('pooch'),
        _py('dask.array', lambda m: m.ones(10, chunks=5).sum().compute(), alias='dask'),
        _py('distributed'),
        _py('dask_gateway', alias='dask-gateway'),
        _py('cvxpy', lambda m: m.Variable(name='x')),
    ),
    *_section(
        'Geo / geoscience',
        _py('dascore'),
        _cli('gmt'),
        _py('obspy', lambda m: m.UTCDateTime('2020-01-01').timestamp),
        _py('obsplus'),
        _py('pygmt'),
    ),
    # The rest of geolab-gmt's additions do real work, in FUNCTIONAL below.
    *_section(
        'geolab-gmt additions',
        _cli('nano'),
    ),
    *_section(
        'Utilities',
        _py('tqdm', lambda m: list(m.tqdm(range(3), disable=True))),
        _py('requests'),
        _py('yaml', lambda m: m.safe_load('a: 1'), alias='pyyaml'),
        _cli('gs'),                    # ghostscript
        _cli('ffmpeg', version_flag='-version'),
    ),
    *_section(
        'Dev tools',
        _cli('gh'),
        _cli('gh-scoped-creds'),
        _py('pytest'),
        _cli('ruff'),
    ),
    *_section(
        'Jupyter stack & extensions',
        _py('jupyterhub'),
        _py('jupyter_server'),
        _py('jupyterlab'),
        _py('ipykernel'),
        _py('jupyter_resource_usage', alias='jupyter-resource-usage'),
        _py('jupyter_ruff', alias='jupyter-ruff'),
        _py('jupyter_server_proxy', alias='jupyter-server-proxy'),
        _py('jupyterlab_git', alias='jupyterlab-git'),
        _py('jupyterlab_myst', alias='jupyterlab-myst'),
        _py('jupyterlab_code_formatter'),
        _py('jupyterlab_pygments'),
        _py('nbdime'),
    ),
    *_section(
        'pip packages & visualization',
        # EarthScope
        _py('earthscope_sdk', alias='earthscope-sdk'),
        _cli('es'),                    # earthscope-cli entry point
        _py('earthscopestraintools'),
        # Jupyter add-ons
        _py('jupyterlab_jupyterbook_navigation'),
        # Visualization & data frames
        _py('altair', lambda m: m.Chart()),
        _py('plotly'),
        _py('polars', lambda m: m.DataFrame({'a': [1, 2]})),
        _py('vegafusion'),
        _py('vl_convert', alias='vl-convert-python'),
        _py('ipympl'),
        _py('hvplot'),
        _py('holoviews', lambda m: m.Curve([1, 2, 3])),
        _py('panel'),
    ),
    *_section(
        'Interactive widgets',
        _py('ipywidgets', lambda m: m.IntSlider(value=5, min=0, max=10)),
        _py('anywidget'),
        _py('bqplot'),
        _py('ipytree', lambda m: m.Node(name='root')),
        _py('itables'),
        _py('ipydatagrid'),
        _py('sidecar', lambda m: m.Sidecar),
    ),
]


def run_py_check(check):
    """Import check.name and run its smoke call; returns the module."""
    mod = importlib.import_module(check.name)
    if check.smoke is not None:
        check.smoke(mod)
    return mod


def run_cli_check(check, cwd):
    """Check that check.name is on $PATH and starts with its version flag.

    Returns the first line of its output. A tool that starts but doesn't
    exit within 10 seconds still counts, as it always has in the notebook.
    """
    path = shutil.which(check.name)
    assert path, f'{check.name} is not on $PATH'
    try:
        r = subprocess.run([path, check.version_flag], cwd=cwd,
                           capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return 'on PATH'
    lines = (r.stdout or r.stderr).strip().splitlines()
    return lines[0] if lines else 'on PATH'


@pytest.mark.parametrize('check', [pytest.param(c, id=c.label) for c in CHECKS if c.kind == 'py'])
def test_import(check):
    run_py_check(check)


@pytest.mark.parametrize('check', [pytest.param(c, id=c.name) for c in CHECKS if c.kind == 'cli'])
def test_cli(check, tmp_path):
    run_cli_check(check, tmp_path)


# ──────────────────────────────────────────────────────────────
# Functional tests, shared with test_notebook.ipynb
# ──────────────────────────────────────────────────────────────
# Each check takes an empty working directory, raises (or fails an
# assert) on failure, and returns a short description of what it did,
# which the notebook shows in its summary table. test_notebook.ipynb runs
# them all with run_functional() in test_helpers.py.

def check_taup(tmp_path):
    """Compute a real P travel time with TauP's bundled iasp91 model."""
    path = shutil.which('taup')
    assert path, 'taup is not on $PATH'
    r = subprocess.run(
        [path, 'time', '-h', '50', '--deg', '60', '--ph', 'P'],
        capture_output=True, text=True, timeout=30, check=True, cwd=tmp_path,
    )
    assert 'iasp91' in r.stdout.lower() and ' P ' in r.stdout, \
        f'unexpected output: {r.stdout!r}'
    return 'computed P travel time (iasp91)'


def check_gmt_map(tmp_path):
    """Render a real coastline map, not just check `gmt --version`."""
    def run(*args):
        subprocess.run(args, cwd=tmp_path, check=True,
                       capture_output=True, text=True, timeout=60)

    run('gmt', 'begin', 'testmap', 'png')
    run('gmt', 'coast', '-R0/10/0/10', '-JM10c', '-Ba', '-Ggray')
    run('gmt', 'end')
    # `gmt end` doesn't reliably remove this session's bookkeeping under
    # ~/.gmt/sessions, and later GMT/PyGMT calls in the same $HOME can
    # read it and decide they're in classic mode, so clear it before
    # anything else (check_pygmt_figure, or the user's own PyGMT code in
    # the notebook's kernel) runs.
    run('gmt', 'clear', 'sessions')

    out = Path(tmp_path) / 'testmap.png'
    assert out.exists() and out.stat().st_size > 0, 'gmt did not produce testmap.png'
    return 'rendered coastline map'


_PYGMT_FIGURE_SCRIPT = """
import sys
from pathlib import Path

import pygmt

out = Path(sys.argv[1]) / "test.png"
fig = pygmt.Figure()
fig.basemap(region=[0, 10, 0, 10], projection="X10c/10c", frame=True)
fig.coast(shorelines=True)
fig.savefig(str(out))
if not (out.exists() and out.stat().st_size > 0):
    sys.exit("figure was not written")
"""


def check_pygmt_figure(tmp_path):
    """Render a figure through GMT's C library, not just import PyGMT.

    In a fresh process: GMT's modern-mode session is process-global
    state, so a separate process keeps other GMT use (in pytest, or the
    notebook's kernel) from affecting it, and the other way round.
    """
    r = subprocess.run([sys.executable, '-c', _PYGMT_FIGURE_SCRIPT, str(tmp_path)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, (r.stderr or r.stdout).strip()[-2000:]
    return 'rendered figure'


def check_gdal_jp2(tmp_path):
    """Write and read back a real JPEG 2000 file, not just check the driver exists."""
    import numpy as np
    from osgeo import gdal

    driver = gdal.GetDriverByName('JP2OpenJPEG')
    assert driver is not None, 'JP2OpenJPEG driver not registered'

    # 64x64, not smaller: JP2's default number of wavelet resolutions is
    # degenerate for tiny images, and real rasters aren't that small.
    size = 64
    mem_ds = gdal.GetDriverByName('MEM').Create('', size, size, 1, gdal.GDT_Byte)
    data = (np.arange(size * size, dtype='uint32') % 256).astype('uint8').reshape(size, size)
    mem_ds.GetRasterBand(1).WriteArray(data)

    # Lossless: the three creation options GDAL documents as required for
    # an exact round trip (YCBCR420 is moot for one band, but real
    # cartographic tiles are RGB).
    # https://gdal.org/en/stable/drivers/raster/jp2openjpeg.html
    out_path = str(Path(tmp_path) / 'test.jp2')
    jp2_ds = driver.CreateCopy(out_path, mem_ds,
                               options=['REVERSIBLE=YES', 'QUALITY=100', 'YCBCR420=NO'])
    jp2_ds = None  # noqa: F841 -- closes and flushes the file
    mem_ds = None

    check_ds = gdal.Open(out_path)
    assert check_ds is not None, 'failed to reopen the JP2 file'
    result = check_ds.GetRasterBand(1).ReadAsArray()
    assert (result == data).all(), 'pixel data did not round-trip losslessly'
    return 'lossless round trip'


FUNCTIONAL = [
    ('taup', check_taup),
    ('gmt (compute)', check_gmt_map),
    ('pygmt (figure)', check_pygmt_figure),
    ('gdal (JP2OpenJPEG)', check_gdal_jp2),
]


@pytest.mark.parametrize('check', [pytest.param(fn, id=label) for label, fn in FUNCTIONAL])
def test_functional(check, tmp_path):
    check(tmp_path)
