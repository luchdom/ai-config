"""Thin executable wrapper over the canonical local-work package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.errors import DeliveryBaseError
    from scripts.redaction import redact_value
    from scripts.workflow_init import WorkflowManager
else:
    from .errors import DeliveryBaseError
    from .redaction import redact_value
    from .workflow_init import WorkflowManager


def _manager(arguments: argparse.Namespace, *, root_name: str = "repository_root") -> WorkflowManager:
    return WorkflowManager(
        getattr(arguments, root_name),
        repository_key=arguments.repository_key,
        state_home_override=arguments.state_home,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="workflow-init")
    subcommands = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repository-root", required=True)
    common.add_argument("--repository-key", required=True)
    common.add_argument("--state-home")

    initialize = subcommands.add_parser("init", parents=[common])
    initialize.add_argument("--workflow", choices=("manual", "semi-autonomous"), required=True)
    initialize.add_argument("--goal", required=True)
    initialize.add_argument("--display-title")
    initialize.add_argument(
        "--completion-boundary",
        choices=("artifact", "working-tree", "commit", "pr", "merge"),
        default="working-tree",
    )

    resume = subcommands.add_parser("resume", parents=[common])
    selectors = resume.add_mutually_exclusive_group(required=True)
    selectors.add_argument("--workflow-id")
    selectors.add_argument("--artifact-path")
    selectors.add_argument("--external-id")

    attach = subcommands.add_parser("attach", parents=[common])
    attach.add_argument("--workflow-id", required=True)
    attach.add_argument("--provider", choices=("linear",), required=True)
    attach.add_argument("--external-id", required=True)

    handoff = subcommands.add_parser("handoff")
    handoff.add_argument("--source-root", required=True)
    handoff.add_argument("--destination-root", required=True)
    handoff.add_argument("--repository-key", required=True)
    handoff.add_argument("--state-home")
    handoff.add_argument("--workflow-id", required=True)
    handoff.add_argument(
        "--expected-path",
        action="append",
        dest="expected_paths",
        required=True,
        help="Exact canonical repo-relative Git-changed path; repeat for each intended path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "init":
            result = _manager(arguments).initialize_local(
                workflow=arguments.workflow,
                goal=arguments.goal,
                display_title=arguments.display_title,
                completion_boundary=arguments.completion_boundary,
            )
        elif arguments.command == "resume":
            result = _manager(arguments).resume(
                workflow_id=arguments.workflow_id,
                artifact_path=arguments.artifact_path,
                external_id=arguments.external_id,
            )
        elif arguments.command == "attach":
            result = _manager(arguments).attach_linear(
                workflow_id=arguments.workflow_id,
                external_id=arguments.external_id,
            )
        else:
            result = WorkflowManager(
                arguments.source_root,
                repository_key=arguments.repository_key,
                state_home_override=arguments.state_home,
            ).workflow_managed_handoff(
                workflow_id=arguments.workflow_id,
                destination_root=arguments.destination_root,
                expected_paths=arguments.expected_paths,
            )
        print(json.dumps(redact_value(result), sort_keys=True))
        return 0
    except DeliveryBaseError as exc:
        print(json.dumps({"status": "failed", "error": redact_value(str(exc))}), file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as exc:
        # Expected machine-environment failures only; programmer defects still surface.
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": f"Expected environment I/O failure ({type(exc).__name__})",
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
