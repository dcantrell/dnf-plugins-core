# Copyright Red Hat, Inc.
# SPDX-License-Identifier: GPL-2.0-or-later
# Assisted-By: Claude

from __future__ import absolute_import
from __future__ import unicode_literals
from tests.support import mock, PkgStub, TestCase, BaseStub, CliStub

import dnf
import dnf.cli
import hawkey
import manifest
import os
import shutil
import tempfile
import unittest

try:
    import libpkgmanifest

    HAVE_LIBPKGMANIFEST = True
except ImportError:
    HAVE_LIBPKGMANIFEST = False


class ManifestCommandTestBase(TestCase):
    """Base class for ManifestCommand tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.base = BaseStub()
        self.cli = CliStub(self.base)
        self.cmd = manifest.ManifestCommand(self.cli)
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)


@unittest.skipUnless(HAVE_LIBPKGMANIFEST, "libpkgmanifest not available")
class ManifestCommandConfigureTest(ManifestCommandTestBase):
    """Test ManifestCommand configuration."""

    def test_configure_new_with_defaults(self):
        """Test configure for 'new' subcommand with default options."""
        self.cmd.opts = mock.Mock()
        self.cmd.opts.subcommand = ["new"]
        self.cmd.opts.input = None
        self.cmd.opts.manifest = None
        self.cmd.opts.use_system = False
        self.cmd.opts.archs = None
        self.cmd.opts.specs = ["foo"]
        self.cmd.opts.source = False
        self.cmd.opts.per_arch = False

        self.cmd.configure()

        self.assertEqual(self.cmd.cmd, "new")
        self.assertEqual(self.cmd.input_file, manifest.DEFAULT_INPUT_FILENAME)
        self.assertEqual(self.cmd.manifest_file, manifest.DEFAULT_MANIFEST_FILENAME)
        self.assertTrue(self.cmd.base.conf.strict)

    def test_configure_new_with_custom_files(self):
        """Test configure for 'new' subcommand with custom file paths."""
        # Create a temporary input file to avoid the existence check
        input_file = os.path.join(self.tmpdir, "custom.in.yaml")
        manifest_file = os.path.join(self.tmpdir, "custom.manifest.yaml")
        with open(input_file, "w") as f:
            f.write("document: rpm-package-input\n")
            f.write('version: "0"\n')

        self.cmd.opts = mock.Mock()
        self.cmd.opts.subcommand = ["new"]
        self.cmd.opts.input = input_file
        self.cmd.opts.manifest = manifest_file
        self.cmd.opts.use_system = False
        self.cmd.opts.archs = None
        self.cmd.opts.specs = []  # No specs, so it will parse the input file
        self.cmd.opts.source = False
        self.cmd.opts.per_arch = False

        with mock.patch.object(self.cmd, "_parse_input"), mock.patch.object(
            self.cmd, "_setup_repositories"
        ):
            self.cmd.configure()

        self.assertEqual(self.cmd.input_file, input_file)
        self.assertEqual(self.cmd.manifest_file, manifest_file)

    def test_configure_new_with_archs(self):
        """Test configure for 'new' subcommand with custom architectures."""
        self.cmd.opts = mock.Mock()
        self.cmd.opts.subcommand = ["new"]
        self.cmd.opts.input = None
        self.cmd.opts.manifest = None
        self.cmd.opts.use_system = False
        self.cmd.opts.archs = ["x86_64", "aarch64"]
        self.cmd.opts.specs = ["foo"]
        self.cmd.opts.source = False
        self.cmd.opts.per_arch = False

        self.cmd.configure()

        self.assertEqual(self.cmd.archs, ["x86_64", "aarch64"])

    def test_configure_new_with_use_system(self):
        """Test configure for 'new' subcommand with --use-system option."""
        self.cmd.opts = mock.Mock()
        self.cmd.opts.subcommand = ["new"]
        self.cmd.opts.input = None
        self.cmd.opts.manifest = None
        self.cmd.opts.use_system = True
        self.cmd.opts.archs = None
        self.cmd.opts.specs = ["foo"]
        self.cmd.opts.source = False
        self.cmd.opts.per_arch = False

        self.cmd.configure()

        self.assertTrue(self.cmd.use_system_repository)

    def test_configure_download(self):
        """Test configure for 'download' subcommand."""
        manifest_file = os.path.join(self.tmpdir, "test.manifest.yaml")
        # Create a minimal manifest file
        with open(manifest_file, "w") as f:
            f.write("document: rpm-package-manifest-input\n")
            f.write('version: "0"\n')

        self.cmd.opts = mock.Mock()
        self.cmd.opts.subcommand = ["download"]
        self.cmd.opts.input = None
        self.cmd.opts.manifest = manifest_file
        self.cmd.opts.use_system = False
        self.cmd.opts.archs = None
        self.cmd.opts.specs = []
        self.cmd.opts.source = False
        self.cmd.opts.destdir = None
        self.cmd.opts.per_arch = False

        with mock.patch.object(self.cmd, "_parse_manifest"):
            self.cmd.configure()

        self.assertEqual(self.cmd.cmd, "download")
        self.assertIsNotNone(self.cmd.download_dir)

    def test_configure_install(self):
        """Test configure for 'install' subcommand."""
        manifest_file = os.path.join(self.tmpdir, "test.manifest.yaml")
        # Create a minimal manifest file
        with open(manifest_file, "w") as f:
            f.write("document: rpm-package-manifest-input\n")
            f.write('version: "0"\n')

        self.cmd.opts = mock.Mock()
        self.cmd.opts.subcommand = ["install"]
        self.cmd.opts.input = None
        self.cmd.opts.manifest = manifest_file
        self.cmd.opts.use_system = False
        self.cmd.opts.archs = None
        self.cmd.opts.specs = []
        self.cmd.opts.source = False
        self.cmd.opts.destdir = None
        self.cmd.opts.per_arch = False

        with mock.patch.object(self.cmd, "_parse_manifest"):
            self.cmd.configure()

        self.assertEqual(self.cmd.cmd, "install")
        self.assertTrue(self.cmd.cli.demands.resolving)


@unittest.skipUnless(HAVE_LIBPKGMANIFEST, "libpkgmanifest not available")
class ManifestCommandChecksumTest(ManifestCommandTestBase):
    """Test checksum conversion methods."""

    def test_rpm_checksum_md5(self):
        """Test RPM checksum conversion for MD5."""
        result = self.cmd._rpm_checksum_type_to_manifest_conversion(1)
        self.assertEqual(result, libpkgmanifest.manifest.ChecksumMethod_MD5)

    def test_rpm_checksum_sha1(self):
        """Test RPM checksum conversion for SHA1."""
        result = self.cmd._rpm_checksum_type_to_manifest_conversion(2)
        self.assertEqual(result, libpkgmanifest.manifest.ChecksumMethod_SHA1)

    def test_rpm_checksum_sha256(self):
        """Test RPM checksum conversion for SHA256."""
        result = self.cmd._rpm_checksum_type_to_manifest_conversion(8)
        self.assertEqual(result, libpkgmanifest.manifest.ChecksumMethod_SHA256)

    def test_rpm_checksum_sha384(self):
        """Test RPM checksum conversion for SHA384."""
        result = self.cmd._rpm_checksum_type_to_manifest_conversion(9)
        self.assertEqual(result, libpkgmanifest.manifest.ChecksumMethod_SHA384)

    def test_rpm_checksum_sha512(self):
        """Test RPM checksum conversion for SHA512."""
        result = self.cmd._rpm_checksum_type_to_manifest_conversion(10)
        self.assertEqual(result, libpkgmanifest.manifest.ChecksumMethod_SHA512)

    def test_rpm_checksum_unknown(self):
        """Test RPM checksum conversion for unknown type."""
        with self.assertRaises(dnf.exceptions.Error):
            self.cmd._rpm_checksum_type_to_manifest_conversion(999)

    def test_dnf_checksum_md5(self):
        """Test DNF checksum conversion for MD5."""
        result = self.cmd._dnf_checksum_type_to_manifest_conversion(hawkey.CHKSUM_MD5)
        self.assertEqual(result, libpkgmanifest.manifest.ChecksumMethod_MD5)

    def test_dnf_checksum_sha1(self):
        """Test DNF checksum conversion for SHA1."""
        result = self.cmd._dnf_checksum_type_to_manifest_conversion(hawkey.CHKSUM_SHA1)
        self.assertEqual(result, libpkgmanifest.manifest.ChecksumMethod_SHA1)

    def test_dnf_checksum_sha256(self):
        """Test DNF checksum conversion for SHA256."""
        result = self.cmd._dnf_checksum_type_to_manifest_conversion(
            hawkey.CHKSUM_SHA256
        )
        self.assertEqual(result, libpkgmanifest.manifest.ChecksumMethod_SHA256)

    def test_dnf_checksum_sha384(self):
        """Test DNF checksum conversion for SHA384."""
        result = self.cmd._dnf_checksum_type_to_manifest_conversion(
            hawkey.CHKSUM_SHA384
        )
        self.assertEqual(result, libpkgmanifest.manifest.ChecksumMethod_SHA384)

    def test_dnf_checksum_sha512(self):
        """Test DNF checksum conversion for SHA512."""
        result = self.cmd._dnf_checksum_type_to_manifest_conversion(
            hawkey.CHKSUM_SHA512
        )
        self.assertEqual(result, libpkgmanifest.manifest.ChecksumMethod_SHA512)

    def test_dnf_checksum_unknown(self):
        """Test DNF checksum conversion for unknown type."""
        with self.assertRaises(dnf.exceptions.Error):
            self.cmd._dnf_checksum_type_to_manifest_conversion(999)


@unittest.skipUnless(HAVE_LIBPKGMANIFEST, "libpkgmanifest not available")
class ManifestCommandHelperTest(ManifestCommandTestBase):
    """Test helper methods."""

    def test_get_arch_generic_url(self):
        """Test URL architecture substitution."""
        url = "http://example.com/repo/x86_64/packages"
        self.base.conf.arch = "x86_64"
        result = self.cmd._get_arch_generic_url(url)
        self.assertEqual(result, "http://example.com/repo/$arch/packages")

    def test_get_src_nevra_from_package(self):
        """Test extracting source NEVRA from package."""
        pkg = PkgStub("foo", "0", "1.0", "1", "x86_64", "test-repo")
        result = self.cmd._get_src_nevra_from_package(pkg)
        self.assertEqual(result, "foo-1.0-1.src")

    def test_get_src_nevra_from_package_no_source(self):
        """Test extracting source NEVRA from package with no source."""
        pkg = mock.Mock()
        pkg.sourcerpm = None
        result = self.cmd._get_src_nevra_from_package(pkg)
        self.assertIsNone(result)

    def test_packages_action_install(self):
        """Test _packages_action with install action."""
        self.cmd.base.install = mock.Mock()
        packages = ["foo", "bar"]
        self.cmd._packages_action(packages, "install")
        self.assertEqual(self.cmd.base.install.call_count, 2)
        self.cmd.base.install.assert_any_call("foo")
        self.cmd.base.install.assert_any_call("bar")

    def test_packages_action_reinstall(self):
        """Test _packages_action with reinstall action."""
        self.cmd.base.reinstall = mock.Mock()
        packages = ["foo"]
        self.cmd._packages_action(packages, "reinstall")
        self.cmd.base.reinstall.assert_called_once_with("foo")

    def test_modules_action_enable(self):
        """Test _modules_action with enable action."""
        self.cmd.module_base = mock.Mock()
        modules = ["module1", "module2"]
        self.cmd._modules_action(modules, "enable")
        self.cmd.module_base.enable.assert_called_once_with(modules)

    def test_modules_action_disable(self):
        """Test _modules_action with disable action."""
        self.cmd.module_base = mock.Mock()
        modules = ["module1"]
        self.cmd._modules_action(modules, "disable")
        self.cmd.module_base.disable.assert_called_once_with(modules)

    def test_modules_action_none(self):
        """Test _modules_action with no modules."""
        self.cmd.module_base = mock.Mock()
        self.cmd._modules_action(None, "enable")
        self.cmd.module_base.enable.assert_not_called()


@unittest.skipUnless(HAVE_LIBPKGMANIFEST, "libpkgmanifest not available")
class ManifestCommandParseTest(ManifestCommandTestBase):
    """Test parsing methods."""

    def test_parse_manifest_nonexistent_file(self):
        """Test parsing nonexistent manifest file raises error."""
        self.cmd.opts = mock.Mock()
        self.cmd.opts.manifest = None
        self.cmd.manifest_file = "/nonexistent/file.yaml"

        with self.assertRaises(dnf.exceptions.Error) as context:
            self.cmd._parse_manifest()
        self.assertIn("does not exist", str(context.exception))

    def test_parse_manifest_single_file(self):
        """Test parsing a single manifest file."""
        manifest_content = """document: rpm-package-manifest
version: "0"
"""
        manifest_file = os.path.join(self.tmpdir, "test.manifest.yaml")
        with open(manifest_file, "w") as f:
            f.write(manifest_content)

        self.cmd.opts = mock.Mock()
        self.cmd.opts.manifest = None
        self.cmd.manifest_file = manifest_file
        self.cmd.archs = ["x86_64"]

        with mock.patch("libpkgmanifest.manifest.Parser") as mock_parser:
            mock_parser_instance = mock.Mock()
            mock_parser.return_value = mock_parser_instance
            self.cmd._parse_manifest()
            mock_parser_instance.parse.assert_called_once_with(manifest_file)


@unittest.skipUnless(HAVE_LIBPKGMANIFEST, "libpkgmanifest not available")
class ManifestCommandRepositoryTest(ManifestCommandTestBase):
    """Test repository setup methods."""

    def test_setup_repositories_with_available(self):
        """Test repository setup skips when using available repositories."""
        self.cmd.use_available_repositories = True
        self.cmd.base.repos.clear = mock.Mock()
        self.cmd._setup_repositories()
        self.cmd.base.repos.clear.assert_not_called()

    def test_setup_repositories_from_input(self):
        """Test repository setup from input object."""
        mock_repo = mock.Mock()
        mock_repo.id = "test-repo"
        mock_repo.baseurl = "http://example.com/repo"
        mock_repo.metalink = None
        mock_repo.mirrorlist = None

        self.cmd.input = mock.Mock()
        self.cmd.input.repositories = [mock_repo]
        self.cmd.manifest = None
        self.cmd.use_available_repositories = False

        self.cmd.base.repos.add_new_repo = mock.Mock()
        self.cmd._setup_repositories()

        self.cmd.base.repos.add_new_repo.assert_called_once()
        call_args = self.cmd.base.repos.add_new_repo.call_args
        self.assertEqual(call_args[0][0], "test-repo")
        self.assertEqual(call_args[1]["baseurl"], ["http://example.com/repo"])

    def test_setup_repositories_from_manifest(self):
        """Test repository setup from manifest object."""
        mock_repo = mock.Mock()
        mock_repo.id = "manifest-repo"
        mock_repo.metalink = "http://example.com/metalink"
        mock_repo.mirrorlist = None
        mock_repo.baseurl = None

        self.cmd.input = None
        self.cmd.manifest = mock.Mock()
        self.cmd.manifest.repositories = [mock_repo]
        self.cmd.use_available_repositories = False

        self.cmd.base.repos.add_new_repo = mock.Mock()
        self.cmd._setup_repositories()

        self.cmd.base.repos.add_new_repo.assert_called_once()
        call_args = self.cmd.base.repos.add_new_repo.call_args
        self.assertEqual(call_args[0][0], "manifest-repo")
        self.assertEqual(call_args[1]["metalink"], "http://example.com/metalink")


@unittest.skipUnless(HAVE_LIBPKGMANIFEST, "libpkgmanifest not available")
class ManifestCommandSourcePackageTest(ManifestCommandTestBase):
    """Test source package handling."""

    def test_parse_source_rpm_nevra(self):
        """Test parsing source RPM NEVRA."""
        dnf_pkg = mock.Mock()
        dnf_pkg.source_name = "foo"
        dnf_pkg.sourcerpm = "foo-1.0-1.src.rpm"

        pkg = mock.Mock()
        pkg.srpm = mock.Mock()

        with mock.patch("rpm.ver") as mock_ver:
            mock_evr = mock.Mock()
            mock_evr.e = None
            mock_evr.v = "1.0"
            mock_evr.r = "1"
            mock_ver.return_value = mock_evr

            self.cmd._parse_source_rpm_nevra(pkg, dnf_pkg)

            self.assertEqual(pkg.srpm.name, "foo")
            self.assertEqual(pkg.srpm.epoch, "0")
            self.assertEqual(pkg.srpm.version, "1.0")
            self.assertEqual(pkg.srpm.release, "1")
            self.assertEqual(pkg.srpm.arch, "src")

    def test_parse_source_rpm_nevra_no_source(self):
        """Test parsing source RPM NEVRA when no source exists."""
        dnf_pkg = mock.Mock()
        dnf_pkg.sourcerpm = None

        pkg = mock.Mock()

        self.cmd._parse_source_rpm_nevra(pkg, dnf_pkg)
        # Should return early without modifying pkg


class ManifestCommandWithoutLibTest(TestCase):
    """Tests that can run without libpkgmanifest."""

    def test_command_registration(self):
        """Test that ManifestCommand has correct aliases."""
        self.assertEqual(manifest.ManifestCommand.aliases, ("manifest",))

    def test_command_summary(self):
        """Test that ManifestCommand has a summary."""
        self.assertIsNotNone(manifest.ManifestCommand.summary)

    def test_default_filenames(self):
        """Test default filename constants."""
        self.assertEqual(manifest.DEFAULT_INPUT_FILENAME, "rpms.in.yaml")
        self.assertEqual(manifest.DEFAULT_MANIFEST_FILENAME, "packages.manifest.yaml")
        self.assertEqual(manifest.MODULE_FILENAME, "modules_dump.modulemd.yaml")
        self.assertEqual(manifest.MODULAR_DATA_SEPARATOR, "...")
