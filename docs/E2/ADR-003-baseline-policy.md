# ADR-003：增量任务的 baseline 策略

状态：课程约束草案，待 A13 确认。

## Context

E2 课件的最小检查要求：删除 INCREMENTAL_CHECK 请求中的 `baseline` 应被拒绝。EChecker 论文原始算法在没有历史实际依赖图时，可以先进行一次 clean build，建立基线后再处理后续提交。

## Decision

当前课程契约要求调用方显式提供与 `base_commit`、`configuration_id` 一致的 baseline。缺少 baseline 的 INCREMENTAL_CHECK 请求在接口校验阶段被拒绝。若需要建立基线，调用方先通过 FULL_CHECK 获取历史图，再创建增量任务。

## Alternatives

在 INCREMENTAL_CHECK 内部自动 clean build 更贴近论文行为，但不符合 E2 对缺 baseline 无效样例的要求，也会模糊本次增量任务是否真正使用了既有基线。

## Consequences

调用方需要额外的基线获取流程。未来若支持论文式回退，需要明确版本升级并更新 Schema、样例和验收测试。
