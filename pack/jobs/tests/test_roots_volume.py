# SPDX-License-Identifier: Apache-2.0
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from pack.orch import roots


@unittest.skipUnless(os.name == 'nt', 'Windows volume API')
class RefsVolumeProbe(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.source = Path(self.temp.name) / 'source'
        self.dest = Path(self.temp.name) / 'output' / 'file'
        self.source.mkdir()
        self.dest.parent.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def probe_error(self, winerror):
        getpath = lambda *_args: 0
        with patch.object(roots, '_api', return_value=getpath), \
             patch.object(roots.C, 'get_last_error', return_value=winerror):
            return roots.refs_same_volume(self.source, self.dest)

    def info_error(self, winerror):
        def getpath(_path, root, _size):
            root.value = 'A:\\'
            return 1

        def getinfo(*_args):
            return 0

        def api(_library, name, *_signature):
            return getpath if name == 'GetVolumePathNameW' else getinfo

        with patch.object(roots, '_api', side_effect=api), \
             patch.object(roots.C, 'get_last_error', return_value=winerror):
            return roots.refs_same_volume(self.source, self.dest)

    def test_unrecognized_network_volume_disables_optional_clone(self):
        self.assertFalse(self.probe_error(1005))

    def test_non_root_volume_path_disables_optional_clone(self):
        self.assertFalse(self.probe_error(144))

    def test_access_denied_is_not_hidden_as_clone_fallback(self):
        with self.assertRaises(OSError) as raised:
            self.probe_error(5)
        self.assertEqual(raised.exception.winerror, 5)

    def test_volume_info_failure_on_network_volume_disables_clone(self):
        self.assertFalse(self.info_error(144))

    def test_volume_info_access_denied_is_not_hidden(self):
        with self.assertRaises(OSError) as raised:
            self.info_error(5)
        self.assertEqual(raised.exception.winerror, 5)


if __name__ == '__main__':
    unittest.main()
