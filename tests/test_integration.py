"""
Test module for testing full maestro integration.
"""

import subprocess

import os
import glob
import pytest
import shutil
import tempfile
import unittest
import time
import datetime


class TestLinkIntegration(unittest.TestCase):
    """Test link integration"""

    @pytest.fixture(autouse=True)
    def spec_path(self, spec_path):
       self.spec_path = spec_path

    # @pytest.fixture(autouse=True)
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # keys and values must have the same number of '/'s
    LINKS_0001 = {
        "run-0001/VAR1.0.36.VAR2.0.17.VAR3.0.44.VAR4.0.39/test-directory-hashing":
           "test-directory-hashing/VAR1.0.3585516934.VAR2.0.1707261687.VAR3.0.4406243939.VAR4.0.3920015696",
        "run-0001/VAR1.0.39.VAR2.0.75.VAR3.0.72.VAR4.0.55/test-directory-hashing":
           "test-directory-hashing/VAR1.0.3874309076.VAR2.0.7520078045.VAR3.0.718718159.VAR4.0.5491000152",
        "run-0001/VAR1.0.84.VAR2.0.73.VAR3.0.90.VAR4.0.19/test-directory-hashing":
           "test-directory-hashing/VAR1.0.8368954934.VAR2.0.7296721416.VAR3.0.8958327389.VAR4.0.1895291838",
    }
    LINKS_0002 = {
        "run-0001/VAR1.0.36.VAR2.0.17.VAR3.0.44.VAR4.0.39/test-directory-hashing": 
            "test-directory-hashing/VAR1.0.3585516934.VAR2.0.1707261687.VAR3.0.4406243939.VAR4.0.3920015696",
        "run-0001/VAR1.0.39.VAR2.0.75.VAR3.0.72.VAR4.0.55/test-directory-hashing": 
            "test-directory-hashing/VAR1.0.3874309076.VAR2.0.7520078045.VAR3.0.718718159.VAR4.0.5491000152",
        "run-0001/VAR1.0.84.VAR2.0.73.VAR3.0.90.VAR4.0.19/test-directory-hashing": 
            "test-directory-hashing/VAR1.0.8368954934.VAR2.0.7296721416.VAR3.0.8958327389.VAR4.0.1895291838",
        "run-0002/VAR1.0.36.VAR2.0.17.VAR3.0.44.VAR4.0.39/test-directory-hashing": 
            "test-directory-hashing/VAR1.0.3585516934.VAR2.0.1707261687.VAR3.0.4406243939.VAR4.0.3920015696",
        "run-0002/VAR1.0.39.VAR2.0.75.VAR3.0.72.VAR4.0.55/test-directory-hashing": 
            "test-directory-hashing/VAR1.0.3874309076.VAR2.0.7520078045.VAR3.0.718718159.VAR4.0.5491000152",
        "run-0002/VAR1.0.84.VAR2.0.73.VAR3.0.90.VAR4.0.19/test-directory-hashing": 
            "test-directory-hashing/VAR1.0.8368954934.VAR2.0.7296721416.VAR3.0.8958327389.VAR4.0.1895291838",
    }
    LINKS_0003 = {
        "run-0001/ITER.10.SIZE.10/echo": 
            "echo/ITER.10.SIZE.10",
        "run-0001/ITER.20.SIZE.10/echo": 
            "echo/ITER.20.SIZE.10",
        "run-0001/ITER.30.SIZE.10/echo": 
            "echo/ITER.30.SIZE.10",
        "run-0001/SIZE.10/post-process-echo-size": 
            "post-process-echo-size/SIZE.10",
        "run-0001/TRIAL.1/post-process-echo-trials": 
            "post-process-echo-trials/TRIAL.1",
        "run-0001/TRIAL.2/post-process-echo-trials": 
            "post-process-echo-trials/TRIAL.2",
        "run-0001/TRIAL.3/post-process-echo-trials": 
            "post-process-echo-trials/TRIAL.3",
        "run-0001/VAR1.0.36.VAR2.0.17.VAR3.0.44.VAR4.0.39/test-directory-hashing": 
            "test-directory-hashing/VAR1.0.3585516934.VAR2.0.1707261687.VAR3.0.4406243939.VAR4.0.3920015696",
        "run-0001/VAR1.0.39.VAR2.0.75.VAR3.0.72.VAR4.0.55/test-directory-hashing": 
            "test-directory-hashing/VAR1.0.3874309076.VAR2.0.7520078045.VAR3.0.718718159.VAR4.0.5491000152",
        "run-0001/VAR1.0.84.VAR2.0.73.VAR3.0.90.VAR4.0.19/test-directory-hashing": 
            "test-directory-hashing/VAR1.0.8368954934.VAR2.0.7296721416.VAR3.0.8958327389.VAR4.0.1895291838",
        "run-0001/all_records/post-process-echo": 
            "post-process-echo",
        "run-0001/all_records/start": 
            "start",
    }

    def compare_tree_to_reference(self, tree, reference):
        tree_lines = tree.split("\n")
        links = []
        for line in tree_lines:
            if line.find(" -> ") > -1:
                links.append(line.split(" -> "))
                links[-1][0] = links[-1][0].split("/")
                links[-1][1] = links[-1][1].split("/")
        assert len(links) == len(reference)
        target_list = list(reference.items())
        for i in range(len(target_list)):
            target_list[i] = [target_list[i][0].split("/"), target_list[i][1].split("/")]
        for a, b in zip(links, target_list):
            assert a[0][-len(b[0]):] == b[0]
            assert a[1][-len(b[1]):] == b[1]

    def test_simple_links(self):
        """
        test simple links
        """
        os.chdir(self.tmp_dir)
        integration_spec_path = self.spec_path("link_integration_fast.yml")

        maestro_cmd = ["maestro", "run", "-fg", "-y", "-s", "1", "--make-links",
               "--link-template", 
               "{{link_directory}}/{{date}}/run-{{INDEX}}/{{instance}}/{{step}}",
               integration_spec_path]
        tree_cmd = ["tree", "-f", "-i", os.path.join(self.tmp_dir, "output", "links")]

        subprocess.run(maestro_cmd)
        cmd_output = subprocess.run(tree_cmd, capture_output=True)
        tree_result = cmd_output.stdout.decode()
        self.compare_tree_to_reference(tree_result, self.LINKS_0001)

        subprocess.run(maestro_cmd)
        cmd_output = subprocess.run(tree_cmd, capture_output=True)
        tree_result = cmd_output.stdout.decode()
        self.compare_tree_to_reference(tree_result, self.LINKS_0002)

    def test_all_links(self):
        """
        test all links
        """
        os.chdir(self.tmp_dir)
        integration_spec_path = self.spec_path("link_integration.yml")

        maestro_cmd = ["maestro", "run", "-fg", "-y", "-s", "1", "--make-links",
               "--link-template", 
               "{{link_directory}}/{{date}}/run-{{INDEX}}/{{instance}}/{{step}}",
               integration_spec_path]
        tree_cmd = ["tree", "-f", "-i", os.path.join(self.tmp_dir, "output", "links")]

        subprocess.run(maestro_cmd)
        cmd_output = subprocess.run(tree_cmd, capture_output=True)
        tree_result = cmd_output.stdout.decode()
        self.compare_tree_to_reference(tree_result, self.LINKS_0003)
