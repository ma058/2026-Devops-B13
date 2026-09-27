"""Recheck an existing DRAFT image against the current committed fixture.

This does not rebuild the Dockerfile or rerun the broken-image baseline.
"""
import argparse
import json

from collect_evidence import ROOT, Recorder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    r = Recorder(args.output, "E3", "draft-existing-image-recheck")
    expected = json.loads((ROOT / "fixtures/draft/expected.json").read_text())
    try:
        cmd, out, _ = r.run(["docker", "image", "inspect", args.image])
        metadata = json.loads(out)[0] if cmd["exit_code"] == 0 else {}
        image_id = metadata.get("Id")
        r.check("image_identity", "existing sha256 image", image_id,
                bool(image_id and image_id.startswith("sha256:")), cmd["id"])
        if image_id:
            r.data["image"] = {"ref": args.image, "id": image_id,
                               "repo_digests": metadata.get("RepoDigests", [])}
            r.data["environment"]["container"] = {
                "os": metadata.get("Os"), "arch": metadata.get("Architecture")}
            for i in range(expected["repeat_count"]):
                cmd, out, _ = r.run(["docker", "run", "--rm", image_id])
                r.check("hello_run_%d" % (i + 1), expected["reference"],
                        {"exit_code": cmd["exit_code"], "stdout": out},
                        cmd["exit_code"] == 0 and out == expected["reference"]["stdout"], cmd["id"])
            # Rebuild current source, not only the historical source baked into the image.
            cmd, out, _ = r.run([
                "docker", "run", "--rm", "-v", str(ROOT / "fixtures/draft") + ":/fixture:ro",
                image_id, "sh", "-c",
                "mkdir /tmp/current && cp /fixture/main.c /fixture/Makefile /tmp/current/ "
                "&& cd /tmp/current && make clean && make && ./hello"])
            r.check("current_fixture_clean_build", "exit 0; last line hello E3",
                    {"exit_code": cmd["exit_code"], "stdout": out},
                    cmd["exit_code"] == 0 and out.splitlines()[-1:] == ["hello E3"], cmd["id"])
            cmd, out, _ = r.run(["docker", "run", "--rm", image_id, "sh", "-c",
                                "cat /etc/os-release; uname -m; make --version; gcc --version; "
                                "git --version; python3 --version; sha256sum /workspace/project/hello"])
            r.data["environment"]["container"]["tool_versions_and_binary_hash"] = out
            r.check("container_metadata", 0, cmd["exit_code"], cmd["exit_code"] == 0, cmd["id"])
        else:
            r.check("container_checks", "available image", "unavailable", status="NOT_RUN")
    except Exception as exc:
        r.check("runner_error", "no exception", repr(exc), False)
    result = r.finish("Existing local image recheck only; current fixture rebuilt in a fresh directory. "
                      "Dockerfile rebuild and broken-image test are outside this recheck scope. "
                      "No LLM or A13 EChecker executed; image is not published to a registry.")
    print(result, r.output)
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
