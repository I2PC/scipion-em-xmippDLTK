# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (delarosatrevin@scilifelab.se) [1]
# *              David Maluenda Niubo (dmaluenda@cnb.csic.es) [2]
# *
# * [1] SciLifeLab, Stockholm University
# * [2] Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************

import json
import re
import os
from datetime import datetime
import pwem
from pyworkflow import Config
import pyworkflow.utils as pwutils
from scipion.install.funcs import CondaCommandDef
from .base import *
from .version import *
from .constants import XMIPP_HOME, XMIPP_URL, XMIPP_DLTK_NAME, XMIPP_CUDA_BIN, XMIPP_CUDA_LIB, XMIPP_GIT_URL, XMIPP3_INSTALLER_URL


_references = ['delaRosaTrevin2013', 'Sorzano2013']
_currentDepVersion = '1.0'
# Requirement version variables
NVIDIA_DRIVERS_MINIMUM_VERSION = 450

type_of_version = version.type_of_version
_logo = version._logo
_currentDepVersion = version._currentDepVersion
__version__ = version.__version__
_xmipp3_installerV = "v2.0.4"


class Plugin(pwem.Plugin):

    @classmethod
    def _defineVariables(cls):
        pass

    @classmethod
    def getEnviron(cls, xmippFirst=True):
        pass

    @classmethod
    def defineBinaries(cls, env):
        pass

def getNvidiaDriverVersion(plugin):
    """Attempt to retrieve the NVIDIA driver version using different methods.
    Only returns if a valid version string is found.
    """
    commands = [
        ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
        ["cat", "/sys/module/nvidia/version"]
    ]

    for cmd in commands:
        try:
            output = subprocess.Popen(
                cmd,
                env=plugin.getEnviron(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ).communicate()[0].decode('utf-8').strip()

            # Check if the output matches a version pattern like 530.30 or 470
            match = re.match(r'^(\d+)', output)
            if match:
                return match.group(1)  # Return just the major version (e.g., "530")

        except (ValueError, TypeError, FileNotFoundError, subprocess.SubprocessError):
            continue  # Try next method

    return None  # No valid version found

def installDeepLearningToolkit(plugin, env):

    preMsgs = []
    cudaMsgs = []
    nvidiaDriverVer = None
    if os.environ.get('CUDA', 'True') == 'True':
        nvidiaDriverVer = getNvidiaDriverVersion(plugin)

    if nvidiaDriverVer is None:
        preMsgs.append("Not nvidia driver found. Type: "
                       " nvidia-smi --query-gpu=driver_version --format=csv,noheader")
        preMsgs.append(
            "CUDA will NOT be USED. (not found or incompatible)")
        msg = ("Tensorflow installed without GPU. Just CPU computations "
               "enabled (slow computations).")
        cudaMsgs.append(msg)
        useGpu = False

    else:
        if int(nvidiaDriverVer) < NVIDIA_DRIVERS_MINIMUM_VERSION:
            preMsgs.append("Incompatible driver %s" % nvidiaDriverVer)
            cudaMsgs.append(f"Your NVIDIA drivers are too old (<{NVIDIA_DRIVERS_MINIMUM_VERSION}). "
                            "Tensorflow was installed without GPU support. "
                            "Just CPU computations enabled (slow computations)."
                            f"To enable CUDA (drivers>{NVIDIA_DRIVERS_MINIMUM_VERSION} needed), "
                            "set CUDA=True in 'scipion.conf' file")
            useGpu = False
        else:
            preMsgs.append("CUDA support found. Driver version: %s" % nvidiaDriverVer)
            msg = "Tensorflow will be installed with CUDA SUPPORT."
            cudaMsgs.append(msg)
            useGpu = True

    # commands  = [(command, target), (cmd, tgt), ...]
    cmdsInstall = list(CondaEnvManager.yieldInstallAllCmds(useGpu=useGpu))

    now = datetime.now()
    installDLvars = {'modelsUrl': "https://scipion.cnb.csic.es/downloads/scipion/software/em",
                     'syncBin': plugin.getHome('bin/xmipp_sync_data'),
                     'modelsDir': plugin.getHome('models'),
                     'modelsPrefix': "models_UPDATED_on",
                     'xmippLibToken': 'xmippLibToken',
                     'libXmipp': plugin.getHome('lib/libXmipp.so'),
                     'preMsgsStr': ' ; '.join(preMsgs),
                     'afterMsgs': ", > ".join(cudaMsgs)}

    installDLvars.update({'modelsTarget': "%s_%s_%s_%s"
                                          % (installDLvars['modelsPrefix'],
                                             now.day, now.month, now.year)})

    modelsDownloadCmd = ("rm %(modelsPrefix)s_* %(xmippLibToken)s 2>/dev/null ; "
                         "echo 'Downloading pre-trained models...' ; "
                         "%(syncBin)s update %(modelsDir)s %(modelsUrl)s DLmodels && "
                         "touch %(modelsTarget)s && echo ' > %(afterMsgs)s'"
                         % installDLvars,                # End of command
                         installDLvars['modelsTarget'])  # Target

    xmippInstallCheck = ("if ls %(libXmipp)s > /dev/null ; "
                         "then touch %(xmippLibToken)s; echo ' > %(preMsgsStr)s' ; "
                         "else echo ; echo ' > Xmipp installation not found, "
                         "please install it first (xmippSrc or xmippBin*).';echo;"
                         " fi" % installDLvars,           # End of command
                         installDLvars['xmippLibToken'])  # Target

    env.addPackage(XMIPP_DLTK_NAME, version='1.0', urlSuffix='external',
                   commands=[xmippInstallCheck]+cmdsInstall+[modelsDownloadCmd],
                   deps=[], tar=XMIPP_DLTK_NAME+'.tgz')
