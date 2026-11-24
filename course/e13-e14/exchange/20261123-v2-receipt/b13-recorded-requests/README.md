# B13 实际请求原件示例

本目录从成员二已核验的个人归档逐字节复制同一个正常任务的6份请求body及summary，非新造请求。来源归档、原路径、源码SHA、job/trace和每个摘要见index.json；未复制认证头、token文件、env、Docker配置或凭据。

依次是 DRAFT → BuildChecker基线 → BuildChecker目标 → EChecker增量 → MDFixer → BuildChecker重检。原协议为 member2-e14-1、同步 POST /v1/run。运行时认证用单独私有 X-E14-Token，不写在body或外发证据中。这些是B13服务协议示例，不保证可原样调用A13现有接口。

所有 /course/work/... 路径、job/trace和image_id均属于历史B13任务，不能直接在A13主机重放。接收方须恢复两版项目、完成适配、创建全新job/trace与输出目录，再依实际DRAFT结果传递新image_id。候选/profile/提交保持固定；不要手改此原件，新的接收方请求另存。

summary的PASS仅表示成员二当次B13项目个人链路，不表示A13已运行或双方已冻结。相应旧代码到PR42的版本桥接已由B13审查记录；联调仍以约定的最终版本另跑。
