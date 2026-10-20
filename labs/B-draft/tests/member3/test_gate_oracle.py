"""成员3：E7 门禁判定函数（evaluate/check_artifacts）的独立测试。

这些测试检查门禁本身的判断能力：伪造的报告字段若违反判定条件，
evaluate() 必须拒绝；合法成功报告必须通过。测试直接调用判定函数并构造
输入，不复制 run_e7_b_gate.py 的实现，也不运行真实 Docker 构建
（真实工作流另有 gate 与 CI 日志）。

运行：python3 -m unittest discover -s tests/member3 -v（在 labs/B-draft 下）
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest

gate_path = next(parent / "scripts/run_e7_b_gate.py" for parent in Path(__file__).resolve().parents
                 if (parent / "scripts/run_e7_b_gate.py").is_file())
spec = importlib.util.spec_from_file_location("gate", gate_path)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

BUILD_IMAGE = "sha256:" + "b" * 64
OTHER_IMAGE = "sha256:" + "c" * 64


def success_report(verify_image=BUILD_IMAGE):
    """构造一份符合 autobuild 输出结构的合法成功报告。"""
    return {
        "trace_id": "e6-b-member3-oracle-test",
        "status": "SUCCEEDED",
        "attempts": [
            {"iteration": 1, "build_exit_code": 1, "failure_class": "MISSING_MAKE"},
            {"iteration": 2, "build_exit_code": 0, "image_id": BUILD_IMAGE},
        ],
        "verification": {
            "command": ["docker", "run", "--rm", "--network", "none", verify_image],
            "exit_code": 0,
            "expected_output": "hello E3",
            "actual_output": "hello E3\n",
            "output_matches": True,
        },
    }


class EvaluateOracleTests(unittest.TestCase):
    def test_accepts_valid_success_report(self):
        """合法成功报告（两轮构建、同镜像、输出匹配）必须通过判定。"""
        gate.evaluate("success", 0, success_report())

    def test_rejects_mismatched_build_and_verify_image(self):
        """构建镜像 ID 与运行镜像 ID 不同的报告必须被拒绝。"""
        report = success_report(verify_image=OTHER_IMAGE)
        with self.assertRaises(ValueError):
            gate.evaluate("success", 0, report)

    def test_rejects_build_timeout_disguised_as_runtime_timeout(self):
        """第二轮构建未成功（构建超时/失败）伪装成运行超时必须被拒绝：
        runtime-timeout 场景要求先确认第二轮 build_exit_code=0。"""
        report = success_report()
        report["attempts"][1]["build_exit_code"] = 1
        report["status"] = "TIMED_OUT"
        report["error"] = "Docker client command exceeded 1s"
        with self.assertRaises(ValueError):
            gate.evaluate("runtime-timeout", 1, report)

    def test_rejects_verification_after_failed_repair_build(self):
        """第二轮构建失败却仍出现 verification 字段的报告必须被拒绝：
        build-failed 场景要求验证未启动。"""
        report = success_report()
        report["attempts"][1]["build_exit_code"] = 1
        report["status"] = "FAILED"
        report["error"] = "Repair candidate build failed; inspect iter-02 logs"
        with self.assertRaises(ValueError):
            gate.evaluate("build-failed", 1, report)


class CheckArtifactsOracleTests(unittest.TestCase):
    def test_rejects_reference_answer_leak_in_artifacts(self):
        """构建上下文出现 Dockerfile.reference（参考答案泄漏）必须被拒绝。"""
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory)
            (evidence / "project").mkdir()
            (evidence / "project/Dockerfile.reference").write_text("leak", encoding="utf-8")
            with self.assertRaises(ValueError):
                gate.check_artifacts("success", evidence, success_report())


if __name__ == "__main__":
    unittest.main()
