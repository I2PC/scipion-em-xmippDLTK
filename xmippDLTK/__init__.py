# **************************************************************************
# *
# * Authors:     Alberto Garcia Mena (alberto.garcia@cnb.csic.es) [1]
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

import re
import os
from datetime import datetime
import pwem
import subprocess
import sys
from conda_envs import DLTK_CONDA_ENVS
import pyworkflow.utils as pwutils

_references = ['delaRosaTrevin2013', 'Sorzano2013']
# Requirement version variables
NVIDIA_DRIVERS_MINIMUM_VERSION = 450
URL_MODELS = "https://scipion.cnb.csic.es/downloads/scipion/software/em"
DLTK_MODELS = "DLTK_MODELS"
DLTK_MODELS_DEFAULT = "dltk-models"
NVIDIA_DRIVER_VAR = 'XMIPP3_NVIDIA_DRIVERS'
_logo = 'xmipp_logo.png'
__version__ = '0.1.0'

class Plugin(pwem.Plugin):

    @classmethod
    def _defineVariables(cls):
        cls._defineVar(DLTK_MODELS, DLTK_MODELS_DEFAULT)

    @classmethod
    def getEnviron(cls):
        pass

    @classmethod
    def defineBinaries(cls, env):
        if not manageCUDA(cls):
            print('scipion-em-xmippDLTK not installed')
            sys.exit(0)
        else:
            syncModels(cls, env)
            for name, env in DLTK_CONDA_ENVS.items():
                versionId = env.get('versionId', None)
                target = f'{name}-{versionId}.yml'
                commandsCreate = []
                commandsCreate.append('conda env create -f %s || conda env update -f %s'
                                % (env['requirements'], env['requirements']))
                commandsCreate.append('touch %s' % target)

                env.addPackage(name, version=versionId,
                               urlSuffix='external',
                               commands=commandsCreate,
                               deps=[], tar=name + '.tgz')




def syncModels(plugin, env):
    cmd = []
    models_home = os.path.join(os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), DLTK_MODELS)

    if os.path.isdir(models_home):
      task = "update"
      in_progress_task = "Updating"
      completed_task = "updated"
    else:
        pwutils.makePath(models_home)
        task = "download"
        in_progress_task = "Downloading"
        completed_task = "downloaded"

    print(f"{in_progress_task} Deep Learning models")

    cmd.append(f'python /sync_data/sync_models.py {task} {models_home} {URL_MODELS} DLmodels')
    env.addPackage(DLTK_MODELS, urlSuffix='external',
                   commands=cmd, deps=[], tar=DLTK_MODELS + '.tgz')



def manageCUDA(plugin):
    nvidiaDriverVer = getNvidiaDriverVersion(plugin)

    if nvidiaDriverVer is None:
        print("Not nvidia driver found. Type: nvidia-smi --query-gpu=driver_version --format=csv,noheader")
        print("CUDA not found or incompatible)")
        return False
    else:
        if int(nvidiaDriverVer) < NVIDIA_DRIVERS_MINIMUM_VERSION:
            print("Incompatible driver %s" % nvidiaDriverVer)
            print(f"Your NVIDIA drivers are too old (<{NVIDIA_DRIVERS_MINIMUM_VERSION}). "
            	f"drivers>{NVIDIA_DRIVERS_MINIMUM_VERSION} needed")
            return False
        else:
            print("CUDA support found. Driver version: %s" % nvidiaDriverVer)
            return True

def getNvidiaDriverVersion(plugin):
    """Attempt to retrieve the NVIDIA driver version using different methods.
    Only returns if a valid version string is found.
    """
    nvidiaDriver =  readNvidiaDriverVar()
    if nvidiaDriver:
        return nvidiaDriver

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

def readNvidiaDriverVar():
    output = os.environ.get(NVIDIA_DRIVER_VAR)
    if output:
        m = re.match(r'^(\d+)', output)
        if m:
            value = m.group(1)
            return value
        else:
            print(f'{NVIDIA_DRIVER_VAR} found but value no valid: {m}')

#
# env.addPackage(XMIPP_DLTK_NAME, version='1.0', urlSuffix='external',
#                    commands=cmdsInstall+[modelsDownloadCmd],
#                    deps=[], tar=XMIPP_DLTK_NAME+'.tgz')


if __name__ == '__main__':
    pl = Plugin()
    pl.defineBinaries(pl.getEnviron())