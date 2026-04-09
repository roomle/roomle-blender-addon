import os
import sys
import unittest
import logging
from shutil import rmtree

from unittest import TestCase
from subprocess import check_call,DEVNULL,CalledProcessError,STDOUT

log = logging.getLogger('test')


def find_blender_executable():
    candidates = []

    env_path = os.environ.get('BLENDER_BIN')
    if env_path:
        candidates.append(env_path)

    candidates.extend([
        '/Applications/Blender.app/Contents/MacOS/Blender',
        '/Applications/Blender.app/Contents/MacOS/blender',
        '/Applications/Blender3.6.2-ARM-LTS.app/Contents/MacOS/blender',
    ])

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    raise FileNotFoundError(
        'No Blender executable found. Set BLENDER_BIN or install Blender in /Applications.'
    )

class RoomleScriptExportTests(TestCase):

    BLENDER = {
        'current': find_blender_executable(),
    }

    scenes = [
        'animation',
        'hierarchy',
        'multimaterial',
        'bounds',
        'hierarchy_rotation',
        'scale',
    ]

    @classmethod
    def setUpClass(self):
        self.cwd = os.path.dirname(os.path.realpath(__file__))
        self.tmp_dir = os.path.join(self.cwd,'tmp')
        os.makedirs(self.tmp_dir,exist_ok=True)

    @classmethod
    def tearDownClass(self):
        # rmtree(self.tmp_dir)
        pass

    def setUp(self):
        test_name = self.id().split('.')[-1]

    def tearDown(self):
        pass

    def run_tests(
        self,
        blender_exe,
        script,
        scene=None,
        out_dir=None
    ):
        args = [
            blender_exe,
            '--background',
        ]

        if scene:
            args += [scene]

        args += [
            '--python',
            script,
            '--',
            self.tmp_dir if out_dir is None else out_dir
        ]
        try:
            check_call(args,cwd=self.cwd,stderr=STDOUT)
            log.debug('Command completed')
        except CalledProcessError as e:
            log.error( 'Command failed! {}'.format(e) +' '.join(args) )
            raise

    def run_test_blend(self,blender_exe,name):
        script = 'test/blend_run_tests.py'
        
        out_dir = os.path.join(self.tmp_dir,name,'test')
        os.makedirs(out_dir,exist_ok=True)
        self.run_tests(blender_exe,script,out_dir=out_dir)

        for scene in self.scenes:
            scene_abs = os.path.join(self.cwd,'assets',scene+'.blend')
            out_dir = os.path.join(self.tmp_dir,name,scene)
            os.makedirs(out_dir,exist_ok=True)
            log.info('loading scene %s',scene_abs)
            self.assertTrue(os.path.isfile(scene_abs))
            self.run_tests(blender_exe,script,scene=scene_abs,out_dir=out_dir)

    def test_fail(self):
        blender_exe = next(iter(self.BLENDER.values()))
        script = 'test/blend_fail.py'
        self.assertRaises( CalledProcessError, self.run_tests, blender_exe, script )

    def test_roomle_script_export(self):
        for name,blender_exe in self.BLENDER.items():
            self.run_test_blend(blender_exe=blender_exe,name=name)

if __name__ == '__main__':

    ## Running a single test 
    # suite = unittest.TestSuite()
    # suite.addTest(DapFbxToAllTests("test_roomle_script_export"))
    # runner = TextTestRunner( verbosity=2 )
    # runner.run(suite)

    test_runner =  unittest.TextTestRunner()
    unittest.main(testRunner=test_runner)
