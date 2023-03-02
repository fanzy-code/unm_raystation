""" 
    Launch Jupyter notebook using a portable web browser executable

    Install firefox portable @ H://portable_software/Firefox_portable/FireFoxPortable.exe
    
    To Do:
    - Raystation paths for connect and system modules by default*

    *Current work around:
    - append 'C:\\Program Files\\RaySearch Laboratories\\RayStation 11B-SP2\\ScriptClient' to sys.path variable prior to using jupyter notebook consoles & scripts
    Note: this is not necessary for scripts executed in Raystation, they have this path already.  This is only a problem for Jupyter development.

    Example code block:


    # Connect to RayStation API
    import os
    import sys
    raystation_pid = os.environ['RAYSTATION_PID']
    ScriptClient_path = 'C:\\Program Files\\RaySearch Laboratories\\RayStation 11B-SP2\\ScriptClient'
    sys.path.append(ScriptClient_path)
    from connect import *

    # Import existing scripts from RayStation
    # Jupyter must be launched from the same virtual environment as where the script is contained
    # The script must exist in RayStation script management, I have not tested if the validated state matters
    environment_scripts_path = os.path.join(os.environ['TEMP'], 'RaySearch\RayStation\Scripts', raystation_pid.split('_')[0], raystation_pid)
    sys.path.append(environment_scripts_path)
    import rs_utils

    
    Permanent solution per ChatGPT:

    The extra_startup_script option should be a path to a file containing the startup script you want to run when 
    Jupyter Notebook starts up. The path can be an absolute or relative file path.

    cli_argv = [
    f"--ServerApp.browser={browser_executable}",
    f"--ServerApp.root_dir='{startup_path}'",
    f"--NotebookApp.extra_startup_script='{startup_script}'",
]

"""

__author__ = "Michael Fan"
__contact__ = "mfan1@unmmg.org"
__version__ = "0.1.0"
__license__ = "MIT"

from jupyterlab import labapp  # type: ignore

browser_executable = "H://portable_software/Firefox_portable/FireFoxPortable.exe %s"
startup_path = "H:/"

# Define CLI Arguments, see https://github.com/jupyter-server/jupyter_server/blob/main/docs/source/users/configuration.rst
# Additional examples, see https://nocomplexity.com/documents/jupyterlab/notebooks/jupyterlab-cli.html
# More examples, see https://jupyter-server.readthedocs.io/en/latest/other/full-config.html
cli_argv = [
    f"--ServerApp.browser={browser_executable}",  # File path to web browser executable
    f"--ServerApp.root_dir='{startup_path}'",  # File path to start-up folder
]

labapp.launch_new_instance(argv=cli_argv)
