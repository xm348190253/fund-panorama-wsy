# 公募基金看板云端更新

每天北京时间 08:00 计划触发采集，校验通过后发布到已有的
[魔搭看板](https://modelscope.cn/studios/wangshuyang2126/fund-panorama-wsy)。
GitHub 调度可能延迟；实际启动和完成时间取决于排队、数据源和部署耗时。

## 首次启用

仓库必须为公开仓库，使用免费的标准 Linux runner。添加 Actions Secret
`MODELSCOPE_API_KEY`（魔搭专用 write token），在 Actions 手动运行一次并核验成功。
配置文件存在不代表首次发布已验收；以实际 Actions 结果和 `last-success.json` 为准。
密钥只存入 GitHub Secrets，不写入代码、聊天或日志。不要选择 admin 权限。

## 更新流程

1. 从现有魔搭代码仓库取得已校验的快照，保留本仓库的前端源文件。
2. 刷新全目录、协会月度规模、批量业绩、缺失成立日期、逐份额详情与风险。
3. 校验全目录采集及字段完整性；网络失败时利用同日检查点重试一次。
4. 生成静态页面和 SHA-256 版本清单，推送原魔搭空间并发起部署。
5. 核对运行中的唯一版本及每个静态资产，成功后保存更新记录。

采集或发布前校验失败时不推送新页面。已推送后若部署、线上核验或记录步骤失败，
红叉仍可能对应已上线的新版本，应查看失败步骤和线上版本后修复或回退；
流水线不自动覆盖并发人工修改，也不承诺平台部署期间零停机。
正常浏览直接打开魔搭链接；刷新只读取云端已发布的静态快照，不触发采集。
旧 ChatGPT Sites 入口按发布清单与 SHA-256 读取魔搭同一份快照；两端不再分别采集。
管理员立即更新入口使用 GitHub 登录与仓库写权限，点击 Run workflow 即可。
每天08:00主触发，08至23点每小时07、17和43分补偿；当天成功后补偿自动跳过。
判断依据是成功回执的 dataDate，而非跨午夜的完成时间。已有运行时复用，生产锁内再次检查。
GitHub 免费调度仍可能延迟，08:00为计划启动时间，不是完成时间。

工作流不启用付费 runner，不保存 Actions artifacts/cache。
本仓库只包含程序及当前公开网页的前端；原始采集缓存、本地研究文件和凭据不上传。
数据每天从公开源采集，成功快照继续存放在原魔搭空间，GitHub 只记录发布结果。
GitHub 公共仓库长期无活动可能暂停定时执行；每日成功记录构成仓库更新，
若任务长期失败或停用，恢复后应手动检查计划是否仍启用。

## 来源和口径

基金数据来自天天基金/东方财富公开来源；全市场规模来自中国证券投资基金业协会，
保留其月末统计日期。每天采集不代表所有字段每日披露，缺口保留真实状态。
界面和部分交互改编自 [Fullgoal_Product_Map](https://github.com/xm348190253/Fullgoal_Product_Map)。
未额外声明整体开源许可证；ECharts 保留原始许可证及版权信息。

参考：[GitHub Actions 计费](https://docs.github.com/en/billing/concepts/product-billing/github-actions)、
[魔搭官方自动部署](https://github.com/modelscope/modelscope-skills/blob/main/skills/ms-studio-deploy/SKILL.md)。
