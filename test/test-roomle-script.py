import os
import unittest
import logging

from subprocess import check_call,DEVNULL,CalledProcessError,STDOUT

from test.utils import TestCaseExtended

log = logging.getLogger('test')

class RoomleScriptExportTests(TestCaseExtended):

    BLENDER = {
        '3.6': '/Applications/Blender3.6.2-ARM-LTS.app/Contents/MacOS/blender',
    }

    scenes = [
        'animation',
        'hierarchy',
        'multimaterial',
        'bounds',
        'hierarchy_rotation',
        'scale',
    ]

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
            self.tmp_path if out_dir is None else out_dir
        ]
        try:
            check_call(args,cwd=self.cwd,stderr=STDOUT)
            log.debug('Command completed')
        except CalledProcessError as e:
            log.error( 'Command failed! {}'.format(e) +' '.join(args) )
            raise

    def run_test_blend(self,blender_exe,name):
        script = 'test/blend_run_tests.py'
        
        out_dir = os.path.join(self.tmp_path,name,'test')
        os.makedirs(out_dir,exist_ok=True)
        self.run_tests(blender_exe,script,out_dir=out_dir)

        for scene in self.scenes:
            scene_abs = os.path.join(self.cwd,'assets',scene+'.blend')
            out_dir = os.path.join(self.tmp_path,name,scene)
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
