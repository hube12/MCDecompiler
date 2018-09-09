#!/usr/bin/python3
# -- Content-Encoding: UTF-8 --
"""
jPype1-py3 installation script
Requires Visual C++ (Express) 2010 to be installed on Windows.
..
    Copyright 2013 Thomas Calmant
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
        http://www.apache.org/licenses/LICENSE-2.0
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""


import os
import sys
import platform
from glob import glob

class NoJDKError(Exception):
    """
    No JDK found
    """
    def __init__(self, possible_homes):
        """
        Sets up the exception message
        """
        Exception.__init__(self, "No JDK found")

        # Normalize possible homes -> always give an iterable or None
        if not possible_homes:
            self.possible_homes = []
        elif not isinstance(possible_homes, (list, tuple)):
            self.possible_homes = [possible_homes]
        else:
            self.possible_homes = possible_homes


class JDKFinder(object):
    """
    Base JDK installation finder
    """
    def __init__(self):
        """
        Sets up the basic configuration
        """
        self.configuration = {
            'include_dirs': [
                os.path.join('native', 'common', 'include'),
                os.path.join('native', 'python', 'include'),
            ],
            'sources': self.find_sources()
        }

    @staticmethod
    def find_sources():
        """
        Sets up the list of files to be compiled
        """
        # Source folders
        common_dir = os.path.join("native", "common")
        python_dir = os.path.join("native", "python")

        # List all .cpp files in those folders
        cpp_files = []
        for folder in (common_dir, python_dir):
            for root, _, file_names in os.walk(folder):
                cpp_files.extend(os.path.join(root, filename)
                                 for filename in file_names
                                 if os.path.splitext(filename)[1] == '.cpp')
        return cpp_files

    def find_jdk_home(self):
        """
        Tries to locate a JDK home folder, according to the JAVA_HOME
        environment variable
        :return: The path to the JDK home
        :raise NoJDKError: No JDK found
        """
        java_home = os.getenv("JAVA_HOME")
        if self.check_jdk(java_home, True):
            return java_home
        else:
            raise NoJDKError(os.getenv("JAVA_HOME"))

    def check_homes(self, homes):
        """
        Checks if one the given folders is a JDK home, and returns it
        :param homes: A list of possible JDK homes
        :return: The first JDK home found, or None
        """
        if isinstance(homes, list):
            homes = {home: False for home in homes}

        for java_home, trusted in homes.items():
            java_home = self.check_jdk(os.path.realpath(java_home), trusted)
            if java_home is not None:
                # Valid path
                return java_home

    def check_jdk(self, java_home, trusted=False):
        """
        Checks if the given folder can be a JDK installation
        :param java_home: A possible JDK installation
        :param trusted: If True, only check if the "include" folder exists
                        (don't try to correct it)
        :return: The real folder path if it contains headers, else None
        """
        if not java_home:
            return
        elif trusted:
            # Trust the path as is, if it exists
            if os.path.exists(os.path.join(java_home, 'include')):
                return os.path.realpath(java_home)
            else:
                return None

        # Find possible JDK folder names
        possible_names = ('jdk', 'java', 'icedtea')

        # Lower-case content tests
        folder = os.path.basename(java_home).lower()

        # Consider it's a JDK if it has an 'include' folder
        # and if the folder name contains 'jdk' or 'java'
        for name in possible_names:
            if name in folder:
                include_path = os.path.join(java_home, 'include')
                if os.path.exists(include_path):
                    # Match
                    return os.path.realpath(java_home)

# ------------------------------------------------------------------------------


class WindowsJDKFinder(JDKFinder):
    """
    Windows specific JDK Finder
    """
    def __init__(self):
        """
        Sets up the basic configuration
        :raise ValueError: No JDK installation found
        """
        # Basic configuration
        JDKFinder.__init__(self)
        self.configuration['libraries'] = ['Advapi32']
        self.configuration['define_macros'] = [('WIN32', 1)]
        self.configuration['extra_compile_args'] = ['/EHsc']

        # Look for the JDK home folder
        java_home = self.find_jdk_home()

        # Home-based configuration
        self.configuration['library_dirs'] = [os.path.join(java_home, 'lib'), ]
        self.configuration['include_dirs'] += [
            os.path.join(java_home, 'include'),
            os.path.join(java_home, 'include', 'win32')
        ]

    def find_jdk_home(self):
        """
        Tries to locate a JDK home folder, according to the JAVA_HOME
        environment variable, or to the Windows registry
        :return: The path to the JDK home
        :raise ValueError: No JDK installation found
        """
        visited_folders = []
        try:
            java_home = JDKFinder.find_jdk_home(self)
            # Found it
            return java_home
        except NoJDKError as ex:
            visited_folders.extend(ex.possible_homes)

        # Try from registry
        java_home = self._get_from_registry()
        if java_home and self.check_jdk(java_home, True):
            return java_home

        # Try with known locations
        # 64 bits (or 32 bits on 32 bits OS) JDK
        possible_homes = glob(
            os.path.join(os.environ['ProgramFiles'], "Java", "*"))
        try:
            # 32 bits (or none on 32 bits OS) JDK
            possible_homes += glob(
                os.path.join(os.environ['ProgramFiles(x86)'], "Java", "*"))
        except KeyError:
            # Environment variable doesn't exist on Windows 32 bits
            pass

        # Compute the real home folder
        java_home = self.check_homes(possible_homes)
        if java_home:
            return java_home
        else:
            visited_folders.extend(possible_homes)
            raise NoJDKError(visited_folders)

    @staticmethod
    def _get_from_registry():
        """
        Retrieves the path to the default Java installation stored in the
        Windows registry
        :return: The path found in the registry, or None
        """
        import winreg
        try:
            jre_hkey = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\JavaSoft\Java Runtime Environment")
            cv = winreg.QueryValueEx(jre_hkey, "CurrentVersion")
            version_hkey = winreg.OpenKey(jre_hkey, cv[0])
            winreg.CloseKey(jre_hkey)

            cv = winreg.QueryValueEx(version_hkey, "RuntimeLib")
            winreg.CloseKey(version_hkey)
            return cv[0]
        except WindowsError:
            pass

# ------------------------------------------------------------------------------


class DarwinJDKFinder(JDKFinder):
    """
    Mac OS X specific JDK Finder
    """
    def __init__(self):
        """
        Sets up the basic configuration
        :raise ValueError: No JDK installation found
        """
        # Basic configuration
        JDKFinder.__init__(self)
        self.configuration['libraries'] = ['dl']
        self.configuration['define_macros'] = [('MACOSX', 1)]

        # Look for the JDK home folder
        java_home = self.find_jdk_home()

        # Home-based configuration
        self.configuration['library_dirs'] = [os.path.join(java_home, 'lib')]
        self.configuration['include_dirs'] += [
            os.path.join(java_home, 'include'),
            os.path.join(java_home, 'include', 'darwin'),
        ]

    def find_jdk_home(self):
        """
        Tries to locate a JDK home folder, according to the JAVA_HOME
        environment variable, or to the Windows registry
        :return: The path to the JDK home
        :raise ValueError: No JDK installation found
        """
        visited_folders = []
        try:
            java_home = JDKFinder.find_jdk_home(self)
            # Found it
            return java_home
        except NoJDKError as ex:
            visited_folders.extend(ex.possible_homes)

        # Changes according to:
        # http://stackoverflow.com/questions/8525193
        # /cannot-install-jpype-on-os-x-lion-to-use-with-neo4j
        # and
        # http://blog.y3xz.com/post/5037243230/installing-jpype-on-mac-os-x
        osx = platform.mac_ver()[0][:4]

        # Seems like the installation folder for Java 7
        possible_homes = glob("/Library/Java/JavaVirtualMachines/*")
        if osx in ('10.7', '10.8'):
            # ... for Java 6
            possible_homes.append('/System/Library/Frameworks/'
                                  'JavaVM.framework/Versions/Current/')
        elif osx == '10.6':
            # Previous Mac OS version
            possible_homes.append('/Developer/SDKs/MacOSX10.6.sdk/System/'
                                  'Library/Frameworks/JavaVM.framework/'
                                  'Versions/1.6.0/')
        else:
            # Other previous version
            possible_homes.append('/Library/Java/Home')

        # Compute the real home folder
        java_home = self.check_homes(possible_homes)
        if java_home:
            return java_home
        else:
            # No JDK found
            visited_folders.extend(possible_homes)
            raise NoJDKError(visited_folders)

    def check_jdk(self, java_home, trusted=False):
        """
        Checks if the given folder can be a JDK installation for Mac OS X
        :param java_home: A possible JDK installation
        :param trusted: If True, only check if the "include" folder exists
                        (don't try to correct it)
        :return: The real folder path if it contains headers, else None
        """
        if not java_home:
            return
        elif trusted:
            # Trust the path as is, if it exists
            if os.path.exists(os.path.join(java_home, 'include')):
                return os.path.realpath(java_home)
            else:
                return None

        # Lower-case content tests
        folder = os.path.basename(java_home).lower()
        if 'jdk' not in folder:
            return

        # Construct the full path
        java_home = os.path.realpath(java_home)
        if not os.path.isdir(java_home):
            return

        # Mac OS specific sub path
        java_home = os.path.join(java_home, 'Contents', 'Home')
        if not os.path.isdir(java_home):
            return

        # Consider it's a JDK if it has an 'include' folder
        # and if the folder name contains 'jdk' or 'java'
        include_path = os.path.join(java_home, 'include')
        if os.path.exists(include_path):
            # Match
            return java_home

# ------------------------------------------------------------------------------


class LinuxJDKFinder(JDKFinder):
    """
    Linux specific JDK Finder
    """
    def __init__(self):
        """
        Sets up the basic configuration
        :raise ValueError: No JDK installation found
        """
        # Basic configuration
        JDKFinder.__init__(self)
        self.configuration['libraries'] = ['dl']

        # Look for the JDK home folder
        java_home = self.find_jdk_home()

        # Home-based configuration
        self.configuration['library_dirs'] = [os.path.join(java_home, 'lib')]
        self.configuration['include_dirs'] += [
            os.path.join(java_home, 'include'),
            os.path.join(java_home, 'include', 'linux'),
        ]

    def find_jdk_home(self):
        """
        Tries to locate a JDK home folder, according to the JAVA_HOME
        environment variable, or to the Windows registry
        :return: The path to the JDK home
        :raise ValueError: No JDK installation found
        """
        visited_folders = []
        try:
            java_home = JDKFinder.find_jdk_home(self)
            # Found it
            return java_home
        except NoJDKError as ex:
            visited_folders.extend(ex.possible_homes)

        # (Almost) standard in GNU/Linux
        possible_homes = glob('/usr/lib/jvm/*')

        # Sun/Oracle Java in some cases
        possible_homes += glob('/usr/java/*')

        # Compute the real home folder
        java_home = self.check_homes(possible_homes)
        if java_home:
            return java_home
        else:
            visited_folders.extend(possible_homes)
            raise NoJDKError(visited_folders)


class CygwinFinder(JDKFinder):
    """
    Linux specific JDK Finder. Works like the Linux finder, with specific
    include directories
    """
    def __init__(self):
        """
        Sets up the basic configuration
        :raise ValueError: No JDK installation found
        """
        # Basic configuration
        JDKFinder.__init__(self)
        self.configuration['libraries'] = ['dl']

        # Look for the JDK home folder, the Linux way
        java_home = LinuxJDKFinder.find_jdk_home(self)

        # Home-based configuration
        self.configuration['library_dirs'] = [os.path.join(java_home, 'lib')]
        self.configuration['include_dirs'] += [
            os.path.join(java_home, 'include'),
            os.path.join('native', 'cygwin'),
            os.path.join(java_home, 'include', 'win32')
        ]

# ------------------------------------------------------------------------------
def main():

    try:
        if sys.platform == 'win32':
            # Windows
            config = WindowsJDKFinder()
        elif sys.platform == 'darwin':
            # MAC OS X
            config = DarwinJDKFinder()
        elif sys.platform == 'cygwin':
            # Cygwin on Windows
            config = CygwinFinder()
        else:
            # Linux / POSIX
            config = LinuxJDKFinder()

    except NoJDKError as no_jdk_ex:
        config = None
        raise RuntimeError(
            "No Java/JDK could be found. I looked in the following directories:"
            "\n\n{0}\n\n"
            "Please check that you have it installed.\n\n"
            "If you have and the destination is not in the above list, please "
            "find out where your java's home is, set your JAVA_HOME environment "
            "variable to that path and retry the installation.\n"
            "If this still fails please open a ticket or create a pull request "
            "with a fix on github:\n"
            "https://github.com/tcalmant/jpype/\n"
            "Here my part: Pls install a JDK for 1.8 and add it to JAVA_HOME"
            .format('\n'.join(no_jdk_ex.possible_homes)))

    return config.configuration["library_dirs"][0]


if __name__=="__main__":
    print(main())