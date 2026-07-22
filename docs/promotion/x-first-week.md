# X 账号首周双语内容包

这组内容用于个人开发者账号的启动，不把账号长期绑定在 Model Economy 上。Model Economy 是第一个公开小项目，后续账号可以继续发布其他工具、实验和开发复盘。

## 发布原则

- X 默认发布英文版，面向 Codex、AI agent 和开源开发工具受众；中文版可用于中文回复、中文技术社区或后续复用。
- 中英文稿表达同一事实，不要求逐字直译。不要在 X 上连续发布内容相同的中英文帖子。
- 每天最多一条原创主帖；发布前后参与相关讨论，回复必须针对原帖内容。
- 不在每条帖子里放仓库链接。需要转化时使用 GitHub 或 Pages，其余帖子优先讨论问题本身。
- 不宣传固定 Token 节省比例，不声称已验证实际模型或角色身份。
- 配图上传 PNG；SVG 是可编辑源文件。中英文图片替代文本随每条内容给出。

## 账号首屏

英文简介：

> I make small software tools and write down what worked, what broke, and why. Project 01: Model Economy.

中文简介：

> 做点小工具，顺手记录哪里好用、哪里翻车、为什么这么做。第一个公开项目：Model Economy。

账号头像使用个人头像或长期个人标识，不使用 Model Economy Logo，避免以后发布其他项目时重新定位。首周将第 1 天帖子置顶；主视觉可作为置顶帖配图，账号横幅需要在 X 客户端单独预览裁切。

## 第 1 天：账号与项目开场

目标：让读者知道这是个人开发者账号，Model Economy 只是第一个公开项目。

英文主帖：

> I’m going to start posting some of the small projects I work on.
>
> First up: Model Economy. It’s a community Codex plugin I made because a one-line edit and a risky migration probably shouldn’t trigger the same workflow.
>
> v0.6.0 is out. I’m looking for the cases where its classifier gets the route wrong.

中文镜像：

> 准备把平时做的一些小项目慢慢发出来。
>
> 第一个是 Model Economy，一个 Codex 社区插件。做它的原因也很直接：改一行代码和做一次高风险迁移，大概不该启动同一套流程。
>
> v0.6.0 已经发布。现在最想知道的，是它会在哪些任务上选错路线。

配图：`assets/promotion/x/builder-workbench.png`

英文替代文本：A developer-style release card showing Model Economy 0.6.0, a healthy local status check, and green macOS, Linux, and Windows release CI.

中文替代文本：一张开发者风格的发布记录图，显示 Model Economy 0.6.0、本地健康状态，以及已经通过的 macOS、Linux、Windows 发行 CI。

英文首条自回复：

> Repo: https://github.com/BottleYo/model-economy
>
> If you try it, I’d like to know where the install is confusing or the routing feels wrong. That’s more useful to me than a star with no feedback.

中文首条自回复：

> 仓库：https://github.com/BottleYo/model-economy
>
> 如果你愿意试一下，我更想知道安装哪里绕、任务分错没有。只有一个 Star、没有反馈，反而帮不到我多少。

## 第 2 天：明确观点

目标：用一个有分歧但能讨论的判断建立主题。

英文主帖：

> One thing still feels wrong in AI coding: the strongest model often ends up doing everything, including the boring stuff.
>
> A field rename and a security-sensitive migration are not the same job. I think the workflow should know that before it starts.

中文镜像：

> AI 编程里有件事我一直觉得不太对：最强模型经常什么都做，连最无聊的活也包了。
>
> 改个字段和处理安全敏感的迁移，根本不是一回事。流程最好在开工前就知道这个区别。

配图：`assets/promotion/x/route-by-risk.png`

英文替代文本：Four task routes: simple work uses the main agent, standard work uses balanced execution, mechanical work uses an economy batch, and high-risk work adds explicit decision and review gates.

中文替代文本：四种任务路线：简单任务由主 agent 完成，标准任务使用 balanced 执行，机械任务使用 economy batch，高风险任务增加明确的决策与终审关口。

英文互动问题：

> What kind of coding task makes you stop and ask for a second review?

中文互动问题：

> 什么样的任务，会让你停下来再找一个人复查？

## 第 3 天：解释插件，不做功能堆砌

目标：让读者在一条帖子里理解 Model Economy 的工作方式。

英文主帖：

> Model Economy is less magical than the name sounds.
>
> It puts a coding task into one of four buckets, then picks a route. Small work stays small. Repetitive work can be batched. Risky work gets architecture and final review.
>
> The interesting part is where the classification gets it wrong. The policy file is public if you want to poke holes in it.

中文镜像：

> Model Economy 没名字听起来那么玄乎。
>
> 它先把任务放进四个分类里，再选路线。小事简单做，重复工作可以批量处理，风险高的任务再加架构和终审。
>
> 真正有意思的是它什么时候会分错。策略文件是公开的，欢迎挑毛病。

配图：`assets/promotion/x/model-economy-flow-en.png`

英文链接回复：

> The routing policy and install docs are here: https://bottleyo.github.io/model-economy/

中文链接回复：

> 路由策略和安装文档：https://bottleyo.github.io/model-economy/#zh-cn

## 第 4 天：主动交代边界

目标：建立可信度，同时为后续实验数据留出空间。

英文主帖：

> A note before I post any numbers: I don’t have a token-savings percentage I trust yet.
>
> The plugin can limit what the workflow asks for. It cannot prove which model actually ran, and policy caps are not billing guarantees.
>
> I’m collecting comparable runs now. Until then, a neat percentage would just be decoration.

中文镜像：

> 先说清楚一件事：我现在还没有一个自己敢信的 Token 节省比例。
>
> 插件能限制流程去请求什么，但它不能证明最后实际跑了哪个模型。策略里的上限，也不等于最终账单。
>
> 我正在收集可以对照的任务。在数据够用之前，写一个漂亮百分比只是装饰。

配图：`assets/promotion/x/claim-boundaries.png`

英文替代文本：Three explicit project boundaries: no fixed token-savings percentage, no verified model or role identity, and policy-level caps are not runtime billing guarantees.

中文替代文本：三条明确边界：不承诺固定 Token 节省比例，不声称已经验证模型或角色身份，策略级上限不是实际账单保证。

## 第 5 天：发布过程复盘

目标：证明项目不是概念图，并自然展示工程完成度。

英文主帖：

> I underestimated how much boring work sits between “it works on my machine” and “someone else can install it.”
>
> The routing rules were done early. The rest was clean installs, repeat installs, upgrades, conflicts, uninstall, two operating modes, three OSes, and making sure the release still worked after all of that.
>
> Not glamorous. Still the part that decides whether the tool is usable.

中文镜像：

> 我低估了“自己电脑能跑”和“别人真的装得上”之间有多少破事。
>
> 路由规则其实很早就写完了。后面全是首次安装、重复安装、升级、冲突、卸载、两种运行模式、三个系统，再把这些塞进一套能走通的发行流程。
>
> 不酷，但工具到底能不能用，就看这些。

配图：`assets/social-preview.png`

英文链接回复：

> The v0.6.0 release and verification notes are here: https://github.com/BottleYo/model-economy/releases/tag/v0.6.0

中文链接回复：

> v0.6.0 发行版和验证记录在这里：https://github.com/BottleYo/model-economy/releases/tag/v0.6.0

## 第 6 天：征集真实任务

目标：获得首批可复现案例，不用赠品换互动。

英文主帖：

> I need a few people to try to break Model Economy’s classifier.
>
> Send me a real task from a public repo: a tiny edit, a feature with clear limits, repetitive cleanup, or something risky enough to deserve a second review.
>
> I’ll post the route it chose, the checks it ran, and where the decision looked wrong.

中文镜像：

> 我想找几个人帮忙把 Model Economy 的分类器搞翻车。
>
> 给我一个公开仓库里的真实任务就行：很小的修改、边界清楚的功能、重复清理，或者值得再找人审一遍的高风险任务。
>
> 我会把它选的路线、做过的检查和判断不对的地方都发出来。

配图：`assets/promotion/x/real-task-wanted.png`

英文替代文本：An open request for public coding tasks in four categories: small edit, bounded feature, mechanical batch, and high-risk change. The card asks for no private code or credentials.

中文替代文本：一张公开征集编程任务的卡片，列出小修改、边界明确的功能、机械批量任务和高风险修改四类示例，并注明不要提交私人代码或认证信息。

筛选标准：只接受可以公开讨论、不会涉及认证信息或私人代码的任务。未经对方许可，不把回复包装成用户背书。

## 第 7 天：一周复盘

目标：把账号重心拉回个人开发过程，为后续其他项目留出口。

英文主帖：

> First week of posting this project. No grand conclusion yet.
>
> The plugin is installable, the routing policy is public, and I’ve written down what I can’t honestly claim yet.
>
> Next comes the useful part: running it on other people’s tasks and seeing where it makes bad calls.

中文镜像：

> 这个项目发出来一周了，暂时没什么宏大结论。
>
> 现在插件能装，路由策略是公开的；哪些话暂时不能说，我也写清楚了。
>
> 接下来才是有用的部分：拿别人的真实任务跑，看它到底会在哪些地方判断失误。

配图：`assets/promotion/x/project-01.png`

英文可选收尾：

> Model Economy is just the first project. I have more small tools to clean up and publish.

中文可选收尾：

> Model Economy 只是第一个。手上还有些小工具，收拾好以后慢慢发。

## 小红书复用

小红书只复用已经在 X 发布过的两个主题，不建立独立选题流水线。英文内容仅作为对照稿，不建议直接发布到小红书。

### 笔记一：我开始公开做一些小工具了

中文标题：`先从一个小项目开始：给 Codex 做任务成本路由`

英文标题参考：`Starting with one small project: risk-based routing for Codex`

中文正文：

> 最近准备把手上做过的小工具慢慢公开。先发 Model Economy，一个 Codex 社区插件。
>
> 做它是因为我不太喜欢所有编程任务都走同一套重流程。改个字段、批量清理代码、做一次高风险迁移，明明不是一类事情。
>
> v0.6.0 已经发布。我仍然没有可信的 Token 节省比例，也没法验证最后实际跑了哪个模型。先让它多跑一些真实任务，看看哪里好用、哪里会分错。

英文参考译文：

> I’m starting to clean up and publish some of the small tools I’ve made. First is Model Economy, a community Codex plugin.
>
> I built it because I don’t like every coding task going through the same heavy workflow. A field change, a batch cleanup, and a risky migration are clearly different jobs.
>
> v0.6.0 is out. I still don’t have a trustworthy token-savings number, and I can’t verify which model actually ran. For now I’m putting real tasks through it and watching where the classifier fails.

配图顺序：`xiaohongshu-01.png`、`xiaohongshu-02.png`、`xiaohongshu-05.png`、`xiaohongshu-06.png`。

### 笔记二：最强模型不该处理所有编程任务

中文标题：`一行修改，也要启动完整 Agent 团队吗？`

英文标题参考：`Does a one-line change need the full agent workflow?`

中文正文：

> 我越来越不喜欢一件事：AI 编程工具经常让最强模型把所有活都干了，连最机械的修改也不例外。
>
> Model Economy 做的事其实很朴素。小改动交给主 agent，重复工作隔离后批量处理，风险高了再加架构和终审。
>
> 这只是路由策略，不是省钱证明。到底少用了多少，要拿相似任务做 A/B；光看角色名字，猜不出来。

英文参考译文：

> One thing in AI coding keeps bothering me: the strongest model often does every job, including the mechanical ones.
>
> Model Economy takes a fairly boring approach. Small edits stay with the main agent, repetitive work gets isolated and batched, and architecture plus final review only show up when the risk is high enough.
>
> That is a routing policy, not proof of savings. Usage needs comparable A/B tasks; role names alone tell us nothing.

配图顺序：六张现有小红书卡片。

## 发布后记录

每条主帖在 24 小时和 7 天后记录：曝光、互动、主页访问、关注增长、GitHub 访问、Stars、Issues、Discussions 和可确认的安装反馈。前 10 条帖子只建立账号自身基线，不套用外部“平均互动率”。
