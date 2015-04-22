import sys, os, glob, shutil, subprocess
from cx_Freeze import setup, Executable
    
import mayavi, tvtk, pyface, wx, traitsui
zip_includes = []
zip_includes.append((os.path.dirname(mayavi.__file__) + "/preferences/preferences.ini", "mayavi/preferences/preferences.ini"))
zip_includes.append((os.path.dirname(mayavi.__file__) + "/core/lut/pylab_luts.pkl", "mayavi/core/lut/pylab_luts.pkl"))
zip_includes.append((os.path.dirname(tvtk.__file__) + "/plugins/scene/preferences.ini", "tvtk/plugins/scene/preferences.ini"))
zip_includes.append((os.path.dirname(pyface.__file__) + "/images/image_not_found.png", "pyface/images/image_not_found.png"))

for file in glob.glob(os.path.join(os.path.dirname(os.path.dirname(tvtk.__file__)),'tvtk','pyface','images','16x16','*.png')):
    zip_includes.append((file, file.split('site-packages\\')[1]))

build_exe_options = {"packages": ["os", "pkg_resources", "wx"], 
                     "excludes": ["tkinter","PyQt4","PySide","scipy","matplotlib"], 
                     "zip_includes": zip_includes}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
#if sys.platform == "win32":
#    base = "Win32GUI"

setup(  name = "envy",
        version = "0.0",
        description = "Phase envelope viewer for binary mixtures!",
        options = {"build_exe": build_exe_options},
        executables = [Executable("envy.py", base=base, compress = False)])

import setuptools
if '.egg' in setuptools.__file__:
    raise ImportError('Cannot package setuptools when in .egg form.  Please uninstall and reinstall with pip, which will give a normal folder')
    
if not os.path.exists('build/exe.win-amd64-2.7/site-packages'):
    os.makedirs('build/exe.win-amd64-2.7/site-packages')

# Manually copy over packages
import mayavi, pyface, wx, traitsui, tvtk

for package in [mayavi,traitsui,pyface,tvtk]:
    olddir = os.path.dirname(package.__file__)
    newdir = os.path.join('build/exe.win-amd64-2.7/site-packages', package.__name__)
    if not os.path.exists(newdir):
        print('copying', olddir, 'to', newdir)
        shutil.copytree(olddir, newdir)
    else:
        print(newdir, 'exists already')
        
subprocess.check_call('for /r %e in (*.exe,*.dll) do ..\upx\upx.exe "%e" --best --compress-icons=0 --nrv2d --crp-ms=999999', cwd = 'build/exe.win-amd64-2.7', stdout = sys.stdout, stderr = sys.stderr, shell = True)
    