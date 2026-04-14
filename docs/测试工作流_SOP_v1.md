# 测试工作流 SOP v1（严格模式）

最后更新：2026-04-14

## 1. 准入门槛（必须全部满足）

每次优化后，先执行严格集成测试。通过标准：

1. `case_records` 落库校验为 `PASSED`
2. 邮件校验为 `PASSED`
3. 每个用例报告中包含完整原始对话

若任一项失败，则该轮回归判定为失败，不进入下一阶段。

---

## 2. 凭证与环境（固定流程）

禁止在文档中保存明文 Token/授权码。统一使用 Keychain：

```bash
# 首次或凭证轮换时执行
scripts/security/save_secrets_to_keychain.sh

# 每次测试前执行
source scripts/security/export_env_from_keychain.sh
```

---

## 3. 严格回归执行

推荐命令：

```bash
scripts/tests/run_strict_regression.sh
```

可指定 run_id：

```bash
scripts/tests/run_strict_regression.sh release_20260414_r1
```

---

## 4. 报告要求（必须）

每个测试用例必须包含：

1. 原始完整对话（用户/客服逐轮）
2. 工单落库证据（case_id、user_id、手机号、车牌、时间）
3. 兜底邮件证据（主题、时间、原文摘录、字段校验）
4. 失败码（若失败）

失败码建议：

- `NO_CASE_RECORD`
- `EMAIL_CHECK_NOT_PASSED`
- `MISSING_PROFILE`
- `AI_SERVICE_CALL_FAILED`

---

## 5. 发布节奏（dev -> 测试项目正式环境）

1. 本地开发并提交到 `dev`
2. Coze 测试项目开发环境拉取 `dev`
3. 部署到测试项目正式环境
4. 执行严格回归
5. 严格回归通过后再进入下一轮优化

---

## 6. 异常处理

1. `401 token invalid`：刷新 Coze 登录态后重试（脚本已内置一次自动重试）
2. 邮件命中失败：先看 `workflow_user_id` 是否写入邮件正文
3. 报告缺字段：按模板补齐后再归档
