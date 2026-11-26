# rsi-flow 原生组合调度

GitTaskBench 14 题和 SkillGenBench 原 10 题分别注册为独立组合流程。组合 ID 使用 `@com.horsecoder.skilllab.liutianyu/workflow/<dataset>/<caseId>`。例如 PDF 元数据题的 ID 为 `@com.horsecoder.skilllab.liutianyu/workflow/skillgenbench/PyPDF2_gtb03`。

注册配置中的三个 `type: flow` 节点通过 `reference` 引用已装配的原子 Skill。准备事件绑定题目输入及产物目录，由 rsi-flow 的 `routes` 依次调度原子节点。节点失败时路由结束，运行记录保留到失败节点。撤销或重装原子 Skill 时，受影响的组合绑定随之更新。

## 实测证据

- Java 8 离线构建成功。24 个不同组合 ID、24 次按 ID 调度，72 个业务节点通过。逐题保存原生流程定义 `*-rsi-flow.json` 与运行记录 `*-run.json`。 [批次汇总](native-proof/platform-summary.json)
- 两组 24 道题的输入和预期产物 SHA-256 均与前次平台记录一致，既有评分可对应到相同产物。此次是引擎接入复验，沿用原实验评分。 [输入和产物核对](native-proof/artifact-continuity.json)
- 48 个项目 Skill 成功注册。撤销 PDF 处理节点后调用组合 ID 返回 409，重载后同一组合 ID 成功；故意让第二节点缺少预期产物，记录只出现前两节点，第三节点被跳过。原来的 `POST /runs` 入口也通过了同题验证。 [注册记录](native-proof/registrations.json) · [撤销重载与失败路由](native-proof/registry-and-failure-route.json)

## 操作

应用前后端对应补丁，启动课程 Spring Boot 工作台并设置其工作区、Python 路径。工作区提供两份 `catalog.json` 及其中声明的原始输入路径。页面照常导入题目的工作流，注册节点并运行，结果展示组合 ID。

服务运行期间，可调用 `PUT /api/skill-lab/v2/workflows`，请求体为现有 `*-workflow.json`。返回的 `id` 是组合 ID，`nodes` 和 `routes` 是已装配的原生定义。随后只传组合 ID 即可调度。

```powershell
Invoke-RestMethod http://127.0.0.1:33486/api/skill-lab/v2/workflows/run `
    -Method Post -ContentType 'application/json' `
    -Body '{"flowId":"@com.horsecoder.skilllab.liutianyu/workflow/skillgenbench/PyPDF2_gtb03"}'
```

在本作业目录可用下面的命令批量注册、运行和导出证据。若服务使用其他端口，替换 `--api`。重启服务会清空运行时注册表，执行同一命令即可恢复注册。命令只调用本地课程服务。

```powershell
python -B reproduction/register_workflows.py run-composite `
    --api http://127.0.0.1:33486/api/skill-lab/v2 `
    --register-catalog --workflow-dir SkillGenBench/platform `
    --workflow-dir GitTaskBench/platform --output native-proof-recheck
```
