"""
Test module for testing link methods.
"""

# @TODO: test cases: index in front, middle, end, no index, two indexes
#        with and without hash
# @TODO: other error checking on template_string?

import os
import pytest
import shutil
import tempfile
import unittest

from maestrowf.utils import (
    splitall, recursive_render, next_path, Linker)
from maestrowf.datastructures.core.study import StudyStep

class TestLinkUtilsUnits(unittest.TestCase):
    """Unit tests for Linker helper functions"""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.sleep_time = 5

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_splitall(self):
        """
        tests splitall method
        """
        dir = os.path.join("foo")
        self.assertEqual(splitall(dir), ["foo"])
        dir = os.path.join("foo", "bar")
        self.assertEqual(splitall(dir), ["foo", "bar"])
        dir = os.path.join("foo", "bar", "foo")
        self.assertEqual(splitall(dir), ["foo", "bar", "foo"])

    def test_validate_study_template(self):
        """
        tests validation of study templates
        """
        # Validate link template: date+time or index; 
        linker = Linker()
        linker.validate_link_template("{{study_index}}")
        linker.validate_link_template("{{output_name}}")
        linker.validate_link_template("{{study_date}}{{study_time}}")
        linker.validate_link_template("{{date}}{{study_time}}")
        with self.assertRaises(ValueError) as context:
            linker.validate_link_template("foo")
        self.assertTrue(
            "does not include required 'study' substrings"
            in str(context.exception))
        with self.assertRaises(ValueError) as context:
            linker.validate_link_template("{{study_date}}")
        self.assertTrue(
            "does not include required 'study' substrings"
            in str(context.exception))
        with self.assertRaises(ValueError) as context:
            linker.validate_link_template("{{date}}")
        self.assertTrue(
            "does not include required 'study' substrings"
            in str(context.exception))
        with self.assertRaises(ValueError) as context:
            linker.validate_link_template("{{study_time}}")
        self.assertTrue(
            "does not include required 'study' substrings"
            in str(context.exception))

    def test_validate_combo_template(self):
        """
        tests validation of study+combo templates
        """
        # Validate link template: date+time or index; 
        linker = Linker(pgen=(lambda x:x))
        linker.validate_link_template("{{study_index}}/{{combo_index}}")
        linker.validate_link_template("{{study_index}}/{{combo}}")
        linker = Linker(
            globals={
                'VAR1': {'label': 'VAR1.%%',
                    'values': [0.3874309076, 0.3585516934, 0.8368954934]},
                'VAR2': {'label': 'VAR2.%%',
                        'values': [0.7520078045, 0.1707261687, 0.7296721416]}})
        linker.validate_link_template("{{study_index}}/{{combo_index}}")
        linker.validate_link_template("{{study_index}}/{{combo}}")
        linker.validate_link_template("{{study_index}}/{{VAR1}}-{{VAR2}}")

        with self.assertRaises(ValueError) as context:
            linker.validate_link_template("{{study_date}}")
        print(context.exception)
        self.assertTrue(
            "does not include required 'study' substrings"
            in str(context.exception))
        self.assertTrue(
            "does not include required 'combo' substrings"
            in str(context.exception))

        with self.assertRaises(ValueError) as context:
            linker.validate_link_template("{{study_index}}")
        self.assertFalse(
            "does not include required 'study' substrings"
            in str(context.exception))
        self.assertTrue(
            "does not include required 'combo' substrings"
            in str(context.exception))

        with self.assertRaises(ValueError) as context:
            linker.validate_link_template("{{combo_index}}")
        self.assertTrue(
            "does not include required 'study' substrings"
            in str(context.exception))
        self.assertFalse(
            "does not include required 'combo' substrings"
            in str(context.exception))
            
        with self.assertRaises(ValueError) as context:
            linker.validate_link_template("{{VAR1}}")
        self.assertTrue(
            "does not include required 'combo' substrings"
            in str(context.exception))

        with self.assertRaises(ValueError) as context:
            linker.validate_link_template("{{combo_index}}{{combo_index}}")
        self.assertTrue(
            "'{{combo_index}}' can not be repeated"
            in str(context.exception))

        with self.assertRaises(ValueError) as context:
            linker.validate_link_template("{{study_index}}{{study_index}}")
        self.assertTrue(
            "'{{study_index}}' can not be repeated"
            in str(context.exception))

    def test_recursive_render(self):
        self.assertEqual(
            recursive_render("Hello {{X}}!", dict(X="{{name}}", name="world")),
            'Hello world!')
        self.assertEqual(
            recursive_render("Hello {{X}}!", dict(X="world")),
            'Hello world!')

    def test_next_path(self):
        """
        tests next_path method
        """
        template = os.path.join(self.tmp_dir, "file-%s.txt")
        file = next_path(template)
        self.assertEqual(file, template % 1)
        max_range = 3
        for i in range(max_range):
            os.system("touch " + (template % i))
        file = next_path(template)
        print(file)
        self.assertEqual(file, template % max_range)
        os.system("touch "+(template % max_range))
        file = next_path(template)
        self.assertEqual(file, template % (max_range + 1))


class TestLinkUtilUnits(unittest.TestCase):
    """Unit tests for Linker class methods"""

    # @TODO rename link_directory to link_directory template
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.sleep_time = 5
        self.linker = Linker()
        self.record = StudyStep()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_split_indexed_directory(self):
        """
        tests split_indexed_directory method
        """
        template_string = (
            "{{output_path_root}}/links/{{date}}/"
            "run-{{study_index}}/{{combo}}/{{step}}")
        split_list = self.linker.split_indexed_directory(template_string)
        self.assertEqual(
            split_list[0],
            ["{{output_path_root}}", "links", "{{date}}"])
        self.assertEqual(
            split_list[1],
            ["{{combo}}", "{{step}}"])
        self.assertEqual(
            split_list[2],
            "run-{{study_index}}")

        template_string = (
            "run-{{study_index}}/{{combo}}/{{step}}")
        split_list = self.linker.split_indexed_directory(template_string)
        self.assertEqual(split_list[0], [])

        template_string = (
            "{{output_path_root}}/links/{{date}}/"
            "run-{{study_index}}")
        split_list = self.linker.split_indexed_directory(template_string)
        self.assertEqual(split_list[1], [])

        template_string = (
            "{{output_path_root}}/links/{{date}}/")
        split_list = self.linker.split_indexed_directory(template_string)
        self.assertEqual(split_list[1], [])
        self.assertEqual(split_list[2], "")

        template_string = (
            "{{output_path_root}}/run-{{study_index}}/{{date}}/"
            "run-{{study_index}}/{{combo}}/{{step}}")
        with pytest.raises(ValueError) as excinfo:
            self.linker.split_indexed_directory(template_string)
        assert ("at most one '{{study_index}}' can be in link"
                in str(excinfo.value))

    def test_build_replacements(self):
        """
        tests split_indexed_directory method
        """
        pass
