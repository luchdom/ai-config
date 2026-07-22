from __future__ import annotations

import copy
import unittest

from tests.linear_delivery_control_plane.support import observation, package, tracking_config


tracking = __import__(package.__name__ + ".tracking", fromlist=["TrackingPreflight"])
NOW = "2026-07-19T12:00:00Z"
REPOSITORY_ID = "repo-" + "a" * 24


class TrackingPreflightTests(unittest.TestCase):
    def test_complete_fixture_passes_without_mutation_or_secret_evidence(self):
        config = tracking_config()
        observed = []

        def inspect(value):
            observed.append(copy.deepcopy(value))
            return observation(value)

        result = tracking.TrackingPreflight(inspect).run(
            config,
            environment={"LINEAR_API_KEY": "sentinel-linear-value"},
            repository_key="ai-config",
            repository_id=REPOSITORY_ID,
            supervisor_version="1.0",
            now=NOW,
        )
        self.assertEqual(result["status"], "ready")
        self.assertFalse(result["mutationPerformed"])
        self.assertNotIn("sentinel-linear-value", repr(result) + repr(observed))

    def test_missing_key_wrong_workspace_and_version_fail_closed(self):
        config = tracking_config()
        checker = tracking.TrackingPreflight(lambda value: observation(value))
        with self.assertRaises(tracking.TrackingPreflightError):
            checker.run(config, environment={}, repository_key="ai-config", repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW)
        wrong = observation(config)
        wrong["workspace"]["id"] = "other"
        with self.assertRaises(tracking.TrackingPreflightError):
            tracking.TrackingPreflight(lambda _: wrong).run(
                config, environment={"LINEAR_API_KEY": "x"},
                repository_key="ai-config", repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW
            )
        with self.assertRaises(tracking.TrackingPreflightError):
            checker.run(config, environment={"LINEAR_API_KEY": "x"}, repository_key="ai-config", repository_id=REPOSITORY_ID, supervisor_version="2.0", now=NOW)

    def test_enabled_ntfy_requires_endpoint_and_topic_but_not_token(self):
        config = tracking_config(ntfy_enabled=True)
        with self.assertRaises(tracking.TrackingPreflightError):
            tracking.resolve_environment(config, {"LINEAR_API_KEY": "x"})
        resolved = tracking.resolve_environment(
            config,
            {"LINEAR_API_KEY": "x", "NTFY_URL": "https://ntfy.sh", "NTFY_TOPIC": "topic"},
        )
        self.assertIsNone(resolved["ntfyToken"])
        with self.assertRaises(tracking.TrackingPreflightError):
            tracking.resolve_environment(
                config,
                {"LINEAR_API_KEY": "x", "NTFY_URL": "https://evil.invalid", "NTFY_TOPIC": "topic"},
            )

    def test_credentials_cannot_be_embedded_in_config(self):
        config = tracking_config()
        config["linear"]["apiKey"] = "forbidden"
        with self.assertRaises(Exception):
            tracking.validate_tracking_config(config)

    def test_attestation_rejects_config_repository_and_expiry_drift(self):
        config = tracking_config()
        preflight = tracking.TrackingPreflight(lambda value: observation(value))
        attestation = preflight.run(
            config, environment={"LINEAR_API_KEY": "x"}, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        preflight.verify_attestation(
            attestation, config=config, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        drifted = copy.deepcopy(config)
        drifted["owner"]["id"] = "attacker"
        with self.assertRaises(tracking.TrackingPreflightError):
            preflight.verify_attestation(
                attestation, config=drifted, repository_key="ai-config",
                repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
            )
        with self.assertRaises(tracking.TrackingPreflightError):
            preflight.verify_attestation(
                attestation, config=config, repository_key="ai-config",
                repository_id="repo-" + "b" * 24, supervisor_version="1.0", now=NOW,
            )
        with self.assertRaises(tracking.TrackingPreflightError):
            preflight.verify_attestation(
                attestation, config=config, repository_key="ai-config",
                repository_id=REPOSITORY_ID, supervisor_version="1.0",
                now="2026-07-19T12:06:00Z",
            )

    def test_forged_copied_extra_and_different_issuer_attestations_are_rejected(self):
        key = b"k" * 32
        config = tracking_config()
        issuer = tracking.TrackingPreflight(
            lambda value: observation(value), issuer_key=key
        )
        attestation = issuer.run(
            config, environment={"LINEAR_API_KEY": "x"}, repository_key="ai-config",
            repository_id=REPOSITORY_ID, supervisor_version="1.0", now=NOW,
        )
        arguments = dict(
            config=config, repository_key="ai-config", repository_id=REPOSITORY_ID,
            supervisor_version="1.0", now=NOW,
        )
        forged = copy.deepcopy(attestation)
        forged["attestationId"] = "preflight-" + "f" * 32
        with self.assertRaises(tracking.TrackingPreflightError):
            issuer.verify_attestation(forged, **arguments)
        copied = copy.deepcopy(attestation)
        copied["ownerId"] = "attacker"
        with self.assertRaises(tracking.TrackingPreflightError):
            issuer.verify_attestation(copied, **arguments)
        extra = copy.deepcopy(attestation)
        extra["extra"] = True
        with self.assertRaises(tracking.TrackingPreflightError):
            issuer.verify_attestation(extra, **arguments)
        other = tracking.TrackingPreflight(lambda value: observation(value))
        with self.assertRaises(tracking.TrackingPreflightError):
            other.verify_attestation(attestation, **arguments)
        with self.assertRaises(TypeError):
            tracking.TrackingPreflight(
                lambda value: observation(value), issuer_key=key,
                claim_binding_id=attestation["claimBindingId"],
            )


if __name__ == "__main__":
    unittest.main()
