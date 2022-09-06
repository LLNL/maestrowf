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
import sys


class TestLinkIntegration(unittest.TestCase):
    """Test link integration"""

    @pytest.fixture(autouse=True)
    def spec_path(self, spec_path):
       self.spec_path = spec_path

    @pytest.fixture(autouse=True)
    def temp_dir(self, temp_dir):
       self.temp_dir = temp_dir

    # @pytest.fixture(autouse=True)
    def setUp(self):
        self.tmp_dir = self.temp_dir()
        
    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # keys and values must have the same number of '/'s
    LINKS_0001_test_study_index = {
        "run-0001/VAR1.0.36.VAR2.0.17.VAR3.0.44.VAR4.0.39/test-directory-hashing":
           "test-directory-hashing/VAR1.0.3585516934.VAR2.0.1707261687.VAR3.0.4406243939.VAR4.0.3920015696",
        "run-0001/VAR1.0.39.VAR2.0.75.VAR3.0.72.VAR4.0.55/test-directory-hashing":
           "test-directory-hashing/VAR1.0.3874309076.VAR2.0.7520078045.VAR3.0.718718159.VAR4.0.5491000152",
        "run-0001/VAR1.0.84.VAR2.0.73.VAR3.0.90.VAR4.0.19/test-directory-hashing":
           "test-directory-hashing/VAR1.0.8368954934.VAR2.0.7296721416.VAR3.0.8958327389.VAR4.0.1895291838",
    }
    LINKS_0002_test_study_index = {
        "run-0001/VAR1.0.36.VAR2.0.17.VAR3.0.44.VAR4.0.39/test-directory-hashing": 
            "test-directory-hashing/VAR1.0.3585516934.VAR2.0.1707261687.VAR3.0.4406243939.VAR4.0.3920015696",
        "run-0001/VAR1.0.39.VAR2.0.75.VAR3.0.72.VAR4.0.55/test-directory-hashing": 
            "test-directory-hashing/VAR1.0.3874309076.VAR2.0.7520078045.VAR3.0.718718159.VAR4.0.5491000152",
        "run-0001/VAR1.0.84.VAR2.0.73.VAR3.0.90.VAR4.0.19/test-directory-hashing": 
            "test-directory-hashing/VAR1.0.8368954934.VAR2.0.7296721416.VAR3.0.8958327389.VAR4.0.1895291838",
        "run-0002/VAR1.0.359.VAR2.0.171.VAR3.0.441.VAR4.0.392/test-directory-hashing":
            "test-directory-hashing/VAR1.0.3585516934.VAR2.0.1707261687.VAR3.0.4406243939.VAR4.0.3920015696",
        "run-0002/VAR1.0.387.VAR2.0.752.VAR3.0.719.VAR4.0.549/test-directory-hashing":
            "test-directory-hashing/VAR1.0.3874309076.VAR2.0.7520078045.VAR3.0.718718159.VAR4.0.5491000152",
        "run-0002/VAR1.0.837.VAR2.0.730.VAR3.0.896.VAR4.0.190/test-directory-hashing":
            "test-directory-hashing/VAR1.0.8368954934.VAR2.0.7296721416.VAR3.0.8958327389.VAR4.0.1895291838",
    }
    LINKS_0001_test_combo_index = {
        "link_integration_test-0001/combo-0001-VAR1.0.36.VAR2.0.17.VAR3.0.44.VAR4.0.39/test-directory-hashing":
            "test-directory-hashing/VAR1.0.3585516934.VAR2.0.1707261687.VAR3.0.4406243939.VAR4.0.3920015696",
        "link_integration_test-0001/combo-0001-VAR1.0.39.VAR2.0.75.VAR3.0.72.VAR4.0.55/test-directory-hashing":
            "test-directory-hashing/VAR1.0.3874309076.VAR2.0.7520078045.VAR3.0.718718159.VAR4.0.5491000152",
        "link_integration_test-0001/combo-0001-VAR1.0.84.VAR2.0.73.VAR3.0.90.VAR4.0.19/test-directory-hashing":
            "test-directory-hashing/VAR1.0.8368954934.VAR2.0.7296721416.VAR3.0.8958327389.VAR4.0.1895291838",
    }
    LINKS_0001_test_hashed_combo_index = {
        "link_integration_test-0001/combo-0001-VAR1.0.36.VAR2.0.17.VAR3.0.44.VAR4.0.39/test-directory-hashing":
            "test-directory-hashing/6df755a183b9e4329be759a718a54f80",
        "link_integration_test-0001/combo-0001-VAR1.0.39.VAR2.0.75.VAR3.0.72.VAR4.0.55/test-directory-hashing":
            "test-directory-hashing/7eb63184e109da27e172188be6e32598",
        "link_integration_test-0001/combo-0001-VAR1.0.84.VAR2.0.73.VAR3.0.90.VAR4.0.19/test-directory-hashing":
            "test-directory-hashing/c74742ecea5a2b58e67350b5a1e0a234",
    }
    LINKS_0001_test_all_links = {
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
    LINKS_0001_test_all_hashed_links = {
        "run-0001/ITER.10.SIZE.10/echo": 
            "echo/d0d800ff9711b3dc32cb29136142d7f8", 
        "run-0001/ITER.20.SIZE.10/echo": 
            "echo/67570ad31cf4fb34283f26ae4571e372", 
        "run-0001/ITER.30.SIZE.10/echo": 
            "echo/b847acec2511954db96eceb1685ee475", 
        "run-0001/SIZE.10/post-process-echo-size": 
            "post-process-echo-size/a42cf0810d88778d90a2facf493c0916", 
        "run-0001/TRIAL.1/post-process-echo-trials": 
            "post-process-echo-trials/d8fc97f2f216f2ffa61981529d1f62c3", 
        "run-0001/TRIAL.2/post-process-echo-trials": 
            "post-process-echo-trials/550f8a61527a7538dcac92e8fed94d6d", 
        "run-0001/TRIAL.3/post-process-echo-trials": 
            "post-process-echo-trials/3018c327f3bd46d1d263d74efc319abf", 
        "run-0001/VAR1.0.36.VAR2.0.17.VAR3.0.44.VAR4.0.39/test-directory-hashing": 
            "test-directory-hashing/6df755a183b9e4329be759a718a54f80", 
        "run-0001/VAR1.0.39.VAR2.0.75.VAR3.0.72.VAR4.0.55/test-directory-hashing": 
            "test-directory-hashing/7eb63184e109da27e172188be6e32598", 
        "run-0001/VAR1.0.84.VAR2.0.73.VAR3.0.90.VAR4.0.19/test-directory-hashing": 
            "test-directory-hashing/c74742ecea5a2b58e67350b5a1e0a234", 
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
            a0, a1 = a[0][-len(b[0]):], a[1][-len(b[1]):]
            print(a0, "==", b[0])
            print(a1, "==", b[1])
            assert a0 == b[0]
            assert a1 == b[1]

    def test_study_index(self):
        """
        test simple study links
        """
        os.chdir(self.tmp_dir)
        integration_spec_path = self.spec_path("link_integration_fast.yml")

        maestro_cmd = ["maestro", "run", "-fg", "-y", "-s", "0", "--make-links",
               "--link-template", 
               "{{output_path}}/../links/{{date}}/run-{{study_index}}/{{combo}}/{{step}}",
               integration_spec_path]
        tree_cmd = ["tree", "-f", "-i", os.path.join(self.tmp_dir, "output", "links")]

        subprocess.run(maestro_cmd)
        print(subprocess.run(["tree", "-f", "-i", self.tmp_dir, "output", "links"], 
            capture_output=True).stdout.decode())
        cmd_output = subprocess.run(tree_cmd, capture_output=True)
        tree_result = cmd_output.stdout.decode()
        self.compare_tree_to_reference(tree_result, self.LINKS_0001_test_study_index)

        maestro_cmd = ["maestro", "run", "-fg", "-y", "-s", "0", "--make-links",
               "--dir-float-format", '{:.3f}', '{:.3e}',
               "--link-template", 
               "{{output_path}}/../links/{{date}}/run-{{study_index}}/{{combo}}/{{step}}",
               integration_spec_path]

        subprocess.run(maestro_cmd)
        cmd_output = subprocess.run(tree_cmd, capture_output=True)
        tree_result = cmd_output.stdout.decode()
        self.compare_tree_to_reference(tree_result, self.LINKS_0002_test_study_index)

    def test_combo_index(self):
        """
        test simple combo links
        """
        os.chdir(self.tmp_dir)
        integration_spec_path = self.spec_path("link_integration_fast.yml")

        maestro_cmd = ["maestro", "run", "-fg", "-y", "-s", "0", "--make-links",
               "--link-template", 
               ("{{output_path}}/../links/{{date}}/{{study_name}}-{{study_index}}/"
                "combo-{{combo_index}}-{{combo}}/{{step}}"),
               integration_spec_path]
        tree_cmd = ["tree", "-f", "-i", os.path.join(self.tmp_dir, "output", "links")]

        subprocess.run(maestro_cmd)
        print("tmp_dir")
        print(subprocess.run(["tree", "-f", "-i", self.tmp_dir], 
            capture_output=True).stdout.decode())
        cmd_output = subprocess.run(tree_cmd, capture_output=True)
        tree_result = cmd_output.stdout.decode()
        print(f"tree_result:\n{tree_result}")
        self.compare_tree_to_reference(tree_result, self.LINKS_0001_test_combo_index)

    def test_hashed_combo_index(self):
        """
        test simple hashed combo links
        """
        os.chdir(self.tmp_dir)
        integration_spec_path = self.spec_path("link_integration_fast.yml")

        maestro_cmd = ["maestro", "run", "-fg", "-y", "-s", "0", "--make-links", "--hashws",
               "--link-template", 
               ("{{output_path}}/../links/{{date}}/{{study_name}}-{{study_index}}/"
                "combo-{{combo_index}}-{{combo}}/{{step}}"),
               integration_spec_path]
        tree_cmd = ["tree", "-f", "-i", os.path.join(self.tmp_dir, "output", "links")]

        subprocess.run(maestro_cmd)
        # print(subprocess.run(["tree", "-f", "-i", self.tmp_dir, "output", "links"], 
        #     capture_output=True).stdout.decode())
        print("tmp_dir")
        print(subprocess.run(["tree", "-f", "-i", self.tmp_dir], 
            capture_output=True).stdout.decode())
        cmd_output = subprocess.run(tree_cmd, capture_output=True)
        tree_result = cmd_output.stdout.decode()
        print(f"tree_result:\n{tree_result}")
        self.compare_tree_to_reference(tree_result, self.LINKS_0001_test_hashed_combo_index)


    def test_all_links(self):
        """
        test all links
        """
        os.chdir(self.tmp_dir)
        integration_spec_path = self.spec_path("link_integration.yml")

        maestro_cmd = ["maestro", "run", "-fg", "-y", "-s", "0", "--make-links",
               "--link-template", 
               "{{output_path}}/../links/{{date}}/run-{{study_index}}/{{combo}}/{{step}}",
               integration_spec_path]
        tree_cmd = ["tree", "-f", "-i", os.path.join(self.tmp_dir, "output", "links")]

        subprocess.run(maestro_cmd)
        cmd_output = subprocess.run(tree_cmd, capture_output=True)
        tree_result = cmd_output.stdout.decode()
        self.compare_tree_to_reference(tree_result, self.LINKS_0001_test_all_links)

    def test_all_hashed_links(self):
        """
        test all links
        """
        os.chdir(self.tmp_dir)
        integration_spec_path = self.spec_path("link_integration.yml")

        maestro_cmd = ["maestro", "run", "-fg", "-y", "-s", "0", "--make-links", "--hashws",
               "--link-template", 
               "{{output_path}}/../links/{{date}}/run-{{study_index}}/{{combo}}/{{step}}",
               integration_spec_path]
        tree_cmd = ["tree", "-f", "-i", os.path.join(self.tmp_dir, "output", "links")]

        subprocess.run(maestro_cmd)
        cmd_output = subprocess.run(tree_cmd, capture_output=True)
        tree_result = cmd_output.stdout.decode()
        print("tree_result\n", tree_result)
        self.compare_tree_to_reference(tree_result, self.LINKS_0001_test_all_hashed_links)

