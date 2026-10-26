"""Baseline-invariant tests for default.json (stdlib only, no network).

Asserts the retained baseline knobs, the security-update exceptions and
that NO rule anywhere re-enables automerge -- a top-level false alone
would be a false green if a packageRule turned automation back on.
"""
import json
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(REPO, "default.json")

with open(DEFAULT, "r", encoding="utf-8") as fh:
    CFG = json.load(fh)


def walk(node):
    """Yield every (key, value) pair in the config tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key, value
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


class TestBaseline(unittest.TestCase):
    def test_base_branch_and_schedule(self):
        self.assertEqual(CFG["baseBranchPatterns"], ["develop"])
        self.assertEqual(CFG["timezone"], "Europe/Berlin")
        self.assertEqual(CFG["schedule"], ["* 0-7 * * 1"])
        self.assertIs(CFG["updateNotScheduled"], False)

    def test_age_limits_and_dashboard(self):
        self.assertEqual(CFG["minimumReleaseAge"], "7 days")
        self.assertEqual(CFG["internalChecksFilter"], "strict")
        self.assertIs(CFG["dependencyDashboard"], True)
        self.assertEqual(CFG["prHourlyLimit"], 2)
        self.assertEqual(CFG["prConcurrentLimit"], 3)
        self.assertEqual(CFG["branchConcurrentLimit"], 3)

    def test_update_hygiene_knobs(self):
        self.assertIs(CFG["ignoreUnstable"], True)
        self.assertIs(CFG["ignoreScripts"], True)
        self.assertIs(CFG["ignorePlugins"], True)
        self.assertIs(CFG["ignoreTests"], False)
        self.assertIs(CFG["pinDigests"], True)
        self.assertEqual(CFG["semanticCommits"], "enabled")
        self.assertIs(CFG["osvVulnerabilityAlerts"], True)
        self.assertIn("group:react", CFG["extends"])
        self.assertIn(":separateMultipleMajorReleases", CFG["extends"])
        self.assertIn("config:recommended", CFG["extends"])
        self.assertIs(CFG["lockFileMaintenance"]["enabled"], True)
        self.assertEqual(CFG["lockFileMaintenance"]["schedule"], ["* 0-7 * * 1"])

    def test_ci_infra_rule_preserved(self):
        rules = [r for r in CFG["packageRules"]
                 if r.get("groupName") == "CI and infrastructure"]
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertEqual(rule["matchManagers"],
                         ["github-actions", "dockerfile", "docker-compose",
                          "devcontainer"])
        self.assertEqual(rule["matchUpdateTypes"],
                         ["minor", "patch", "pin", "pinDigest", "digest"])
        self.assertEqual(rule["matchJsonata"], [
            "$not(enabled = false) and $not(dependencyDashboardApproval = true) "
            "and $not(isVulnerabilityAlert = true)"])
        self.assertNotIn("automerge", rule,
                         "infra rule inherits top-level automerge=false")

    def test_no_automerge_anywhere(self):
        self.assertIs(CFG["automerge"], False)
        self.assertIs(CFG["platformAutomerge"], False)
        for key, value in walk(CFG):
            if key in ("automerge", "platformAutomerge"):
                self.assertIs(value, False,
                              "%s must be exactly false everywhere" % key)

    def test_major_rule_manual_approval_no_automerge(self):
        majors = [r for r in CFG["packageRules"]
                  if "major" in r.get("matchUpdateTypes", [])]
        self.assertTrue(majors, "major rule missing")
        for rule in majors:
            self.assertIs(rule.get("dependencyDashboardApproval"), True)
            self.assertIs(rule.get("automerge"), False)


class TestSecurityExceptions(unittest.TestCase):
    def test_vulnerability_alerts_bypass_gates(self):
        va = CFG["vulnerabilityAlerts"]
        self.assertIs(va["enabled"], True)
        self.assertEqual(va["schedule"], ["at any time"])
        self.assertIs(va["updateNotScheduled"], True)
        self.assertIsNone(va["minimumReleaseAge"])
        self.assertIsNone(va["groupName"])
        self.assertIs(va["dependencyDashboardApproval"], False)
        self.assertEqual(va["prConcurrentLimit"], 0)
        self.assertEqual(va["prHourlyLimit"], 0)
        self.assertEqual(va["branchConcurrentLimit"], 0)
        self.assertIs(va["automerge"], False)
        self.assertEqual(va["labels"], ["dependencies", "security"])

    def test_no_rule_silently_enables_automerge_for_security(self):
        # security rules must also keep automerge off; walk() covers this,
        # here we additionally check every packageRule explicitly.
        for rule in CFG["packageRules"]:
            if "automerge" in rule:
                self.assertIs(rule["automerge"], False)


class TestValidationWorkflow(unittest.TestCase):
    def test_ci_runs_the_real_validator_and_its_regressions(self):
        path = os.path.join(REPO, ".github", "workflows", "checks.yml")
        with open(path, "r", encoding="utf-8") as fh:
            workflow = fh.read()
        self.assertIn("node --test tests/validation.test.mjs", workflow)
        self.assertIn(
            'node scripts/validate-preset.mjs "$RENOVATE_VALIDATOR" default.json',
            workflow)
        self.assertIn("export RENOVATE_VALIDATOR", workflow)
        self.assertIn("--ignore-scripts", workflow)
        self.assertRegex(workflow, r"--package=renovate@\d+\.\d+\.\d+")


if __name__ == "__main__":
    unittest.main()
